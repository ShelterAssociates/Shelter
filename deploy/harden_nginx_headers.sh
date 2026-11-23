#!/bin/bash
# Stop nginx announcing itself:
#  - http block of nginx.conf: "server_tokens off" (no version or OS anywhere) and,
#    when the headers-more module is installed (Ubuntu package nginx-extras),
#    "more_clear_headers Server" (no Server header at all);
#  - installs deploy/nginx_error_pages.conf as /etc/nginx/snippets/shelter-error-pages.conf
#    for the server blocks to include (generic error and redirect pages).
#
#   sudo deploy/harden_nginx_headers.sh           show the changes, change nothing
#   sudo deploy/harden_nginx_headers.sh --apply   back up, change, nginx -t (restores on failure)
#   then: sudo service nginx reload
set -euo pipefail

NGINX=${NGINX:-nginx}
CONF=$(readlink -f "${NGINX_CONF:-/etc/nginx/nginx.conf}")
SNIPPET_SRC="$(cd "$(dirname "$0")" && pwd)/nginx_error_pages.conf"
SNIPPET=${SNIPPET:-/etc/nginx/snippets/shelter-error-pages.conf}

if "$NGINX" -V 2>&1 | grep -q "headers-more"; then
    has_headers_more=yes
else
    has_headers_more=no
    echo "headers-more module not installed: the Server header will say just \"nginx\"."
    echo "To remove it completely: sudo apt-get install nginx-extras, then run this again."
fi

stage=$(mktemp)
trap 'rm -f "$stage"' EXIT
sed -E "s|^([[:space:]]*)#?[[:space:]]*server_tokens[[:space:]][^;]*;.*|\1server_tokens off;|" "$CONF" > "$stage"
grep -qE "^[[:space:]]*server_tokens off;" "$stage" ||
    sed -i -E "0,/^[[:space:]]*http[[:space:]]*\{/s||&\n\tserver_tokens off;|" "$stage"
if [ "$has_headers_more" = yes ] && ! grep -qE "^[[:space:]]*more_clear_headers[[:space:]]+\"?Server\"?[[:space:]]*;" "$stage"; then
    sed -i -E "0,/^([[:space:]]*)server_tokens off;.*/s||&\n\1more_clear_headers Server;|" "$stage"
fi
grep -qE "^[[:space:]]*server_tokens off;" "$stage" || { echo "STOP: no http { block found in $CONF" >&2; exit 1; }

conf_changes=yes; cmp -s "$CONF" "$stage" && conf_changes=no
snippet_changes=yes; cmp -s "$SNIPPET_SRC" "$SNIPPET" 2>/dev/null && snippet_changes=no

if [ $conf_changes = no ] && [ $snippet_changes = no ]; then
    echo "Nothing to change: version hidden, Server header removed: $has_headers_more, snippet $SNIPPET up to date."
    exit 0
fi
[ $conf_changes = yes ] && { diff -u "$CONF" "$stage" | sed "1,2s|$stage|$CONF (new)|" || true; }
[ $snippet_changes = yes ] && echo "Will install $SNIPPET (from $SNIPPET_SRC)."
if [ "${1:-}" != "--apply" ]; then
    echo
    echo "Dry run: nothing changed. Run again with --apply to make these changes."
    exit 0
fi

backup=${BACKUP_DIR:-/root/nginx-headers-backup-$(date +%Y%m%d-%H%M%S)}
mkdir -p "$backup"
cp --parents -p "$CONF" "$backup"
[ -f "$SNIPPET" ] && cp --parents -p "$SNIPPET" "$backup"
cat "$stage" > "$CONF"
mkdir -p "$(dirname "$SNIPPET")"
cp "$SNIPPET_SRC" "$SNIPPET"
if "$NGINX" -t; then
    echo "Done. Backup of the old files: $backup"
    echo "Next: add 'include $SNIPPET;' to every server block (see the deploy notes), nginx -t, then:"
    echo "      sudo service nginx reload"
else
    cat "$backup$CONF" > "$CONF"
    if [ -f "$backup$SNIPPET" ]; then cat "$backup$SNIPPET" > "$SNIPPET"; fi
    echo "nginx -t failed: nginx.conf restored, nothing changed. Backup: $backup" >&2
    exit 1
fi
