#!/bin/bash
# Strong TLS for every nginx site on this server: TLS 1.2 (plus 1.3 when nginx
# and OpenSSL support it) with ECDHE + AES-GCM / ChaCha20 cipher suites only.
#
# Sets ssl_protocols, ssl_ciphers and ssl_prefer_server_ciphers wherever they
# already appear (nginx.conf, sites-enabled, conf.d, certbot's
# options-ssl-nginx.conf) and adds them to the http block of nginx.conf, which
# covers every server that has no TLS lines of its own (catch-all, report, graphs).
# Old nginx picks the protocol from the default server before SNI, so the http
# block matters even when each site has its own settings.
#
#   sudo deploy/harden_nginx_tls.sh           show the changes, change nothing
#   sudo deploy/harden_nginx_tls.sh --apply   back up, change, nginx -t (restores on failure)
#   then: sudo service nginx reload
set -euo pipefail

CIPHERS="ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305"
NGINX=${NGINX:-nginx}
ETC=${NGINX_ETC:-/etc/nginx}
CERTBOT_OPTIONS=${CERTBOT_OPTIONS:-/etc/letsencrypt/options-ssl-nginx.conf}

at_least() { [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -1)" = "$2" ]; }

info=$("$NGINX" -V 2>&1)
nginx_version=$(echo "$info" | sed -n 's|^nginx version: nginx/\([0-9.]*\).*|\1|p')
openssl_version=$(echo "$info" | sed -n 's/^built with OpenSSL \([0-9.]*\).*/\1/p' | head -1)
[ -n "$openssl_version" ] || openssl_version=$(openssl version 2>/dev/null | awk '{print $2}' | tr -d '[:alpha:]-')
PROTOCOLS="TLSv1.2"
if at_least "$nginx_version" 1.13.0 && at_least "${openssl_version:-0}" 1.1.1; then
    PROTOCOLS="TLSv1.2 TLSv1.3"
fi
echo "nginx $nginx_version, OpenSSL ${openssl_version:-unknown} -> ssl_protocols $PROTOCOLS"

files=()
for f in "$ETC/nginx.conf" "$ETC"/sites-enabled/* "$ETC"/conf.d/*.conf "$CERTBOT_OPTIONS"; do
    [ -f "$f" ] || continue
    real=$(readlink -f "$f")
    [[ " ${files[*]-} " == *" $real "* ]] || files+=("$real")
done

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
changed=()
for f in "${files[@]}"; do
    out="$stage/$(echo "$f" | tr / _)"
    if grep -qE '^[[:space:]]*ssl_ciphers[[:space:]][^;]*$' "$f"; then
        echo "STOP: $f has an ssl_ciphers value spread over several lines; fix it by hand." >&2
        exit 1
    fi
    sed -E \
        -e "s|^([[:space:]]*)ssl_protocols[[:space:]][^;]*;.*|\1ssl_protocols $PROTOCOLS;|" \
        -e "s|^([[:space:]]*)ssl_ciphers[[:space:]][^;]*;.*|\1ssl_ciphers $CIPHERS;|" \
        -e "s|^([[:space:]]*)ssl_prefer_server_ciphers[[:space:]][^;]*;.*|\1ssl_prefer_server_ciphers on;|" \
        "$f" > "$out"
    if [ "$f" = "$(readlink -f "$ETC/nginx.conf")" ]; then
        for directive in "ssl_prefer_server_ciphers on;" "ssl_ciphers $CIPHERS;" "ssl_protocols $PROTOCOLS;"; do
            name=${directive%% *}
            grep -qE "^[[:space:]]*$name[[:space:]]" "$out" ||
                sed -i -E "0,/^[[:space:]]*http[[:space:]]*\{/s||&\n\t$directive|" "$out"
        done
        grep -qE "^[[:space:]]*ssl_protocols $PROTOCOLS;" "$out" || { echo "STOP: no http { block found in $f" >&2; exit 1; }
    fi
    if ! cmp -s "$f" "$out"; then
        changed+=("$f")
        diff -u "$f" "$out" | sed "1,2s|$out|$f (new)|" || true
    fi
done

if [ ${#changed[@]} -eq 0 ]; then
    echo "Nothing to change: TLS settings are already strong."
    exit 0
fi
if [ "${1:-}" != "--apply" ]; then
    echo
    echo "Dry run: nothing changed. Run again with --apply to make these changes."
    exit 0
fi

backup=${BACKUP_DIR:-/root/nginx-tls-backup-$(date +%Y%m%d-%H%M%S)}
mkdir -p "$backup"
for f in "${changed[@]}"; do
    cp --parents -p "$f" "$backup"
    cat "$stage/$(echo "$f" | tr / _)" > "$f"
done
if "$NGINX" -t; then
    echo "Done. Backup of the old files: $backup"
    echo "Now reload: sudo service nginx reload"
else
    for f in "${changed[@]}"; do cat "$backup$f" > "$f"; done
    echo "nginx -t failed: old files restored, nothing changed. Backup: $backup" >&2
    exit 1
fi
