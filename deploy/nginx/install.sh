#!/bin/bash
# Installs this repo's nginx site file for one environment as
# /etc/nginx/sites-enabled/shelter_nginx (and the same copy in sites-available).
#
#   sudo deploy/nginx/install.sh uat|prod           show the diff, change nothing
#   sudo deploy/nginx/install.sh uat|prod --apply   back up, copy, nginx -t (restores on failure)
#   then: sudo service nginx reload
#
# Run deploy/harden_nginx_headers.sh --apply first: the site file includes the
# error-pages snippet that script installs.
set -euo pipefail

ENV=${1:-}
case "$ENV" in
    prod) HOST=app.shelter-associates.org ;;
    uat) HOST=uat.shelter-associates.org ;;
    *) echo "usage: $0 uat|prod [--apply]" >&2; exit 2 ;;
esac
NGINX=${NGINX:-nginx}
ETC=${NGINX_ETC:-/etc/nginx}
SRC="$(cd "$(dirname "$0")" && pwd)/$ENV.conf"
DEST="$ETC/sites-enabled/shelter_nginx"
COPY="$ETC/sites-available/shelter_nginx"
SNIPPET="$ETC/snippets/shelter-error-pages.conf"

if [ ! -f "$SNIPPET" ]; then
    echo "STOP: $SNIPPET is missing. Run deploy/harden_nginx_headers.sh --apply first." >&2
    exit 1
fi
if [ -f "$DEST" ] && ! grep -qE "server_name[[:space:]]+$HOST;" "$DEST"; then
    echo "STOP: $DEST does not serve $HOST - is this really the $ENV server?" >&2
    exit 1
fi
for f in "$ETC"/sites-enabled/*; do
    [ -e "$f" ] || continue
    [ "$(readlink -f "$f")" = "$(readlink -f "$DEST")" ] && continue
    echo "NOTE: another enabled site: $f (it is kept; check it does not use default_server)."
done

if [ -f "$DEST" ] && cmp -s "$SRC" "$DEST"; then
    echo "Nothing to change: $DEST already matches $SRC."
    exit 0
fi
diff -u "$DEST" "$SRC" || true
if [ "${2:-}" != "--apply" ]; then
    echo
    echo "Dry run: nothing changed. Run again with --apply to install $SRC."
    exit 0
fi

backup=${BACKUP_DIR:-/root/nginx-site-backup-$(date +%Y%m%d-%H%M%S)}
mkdir -p "$backup"
for f in "$DEST" "$COPY"; do
    if [ -f "$f" ]; then cp --parents -p "$f" "$backup"; fi
done
cp "$SRC" "$DEST"
cp "$SRC" "$COPY"
if "$NGINX" -t; then
    echo "Done. Backup of the old files: $backup"
    echo "Now reload: sudo service nginx reload"
else
    for f in "$DEST" "$COPY"; do
        if [ -f "$backup$f" ]; then cat "$backup$f" > "$f"; fi
    done
    echo "nginx -t failed: old site file restored, nothing changed. Backup: $backup" >&2
    exit 1
fi
