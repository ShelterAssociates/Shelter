#!/bin/bash
# Points this server's BIRT report designs at THIS server's app, so UAT reports
# read UAT data and prod reports read prod data. The designs (FFReport, RIMReport,
# DrainageReport ...) fetch data and images from a hard-coded app address; only
# that hostname is changed (uat <-> app), nothing else.
# Also lists every address and database host the designs use, for review.
#
#   sudo deploy/birt/set_report_host.sh uat|prod           show the changes, change nothing
#   sudo deploy/birt/set_report_host.sh uat|prod --apply   back up, change in place
#   then: sudo service tomcat7 restart
#
# Design folder: /var/lib/tomcat7/webapps/Birt (BIRT_DIR=... to change);
# more design files: DESIGNS="/path/a.rptdesign /path/b.rptdesign".
set -euo pipefail

case "${1:-}" in
    uat) FROM=app.shelter-associates.org; TO=uat.shelter-associates.org ;;
    prod) FROM=uat.shelter-associates.org; TO=app.shelter-associates.org ;;
    *) echo "usage: $0 uat|prod [--apply]" >&2; exit 2 ;;
esac
BIRT_DIR=${BIRT_DIR:-/var/lib/tomcat7/webapps/Birt}

files=()
for f in "$BIRT_DIR"/*.rptdesign ${DESIGNS:-}; do
    [ -f "$f" ] || continue
    real=$(readlink -f "$f")
    [[ " ${files[*]-} " == *" $real "* ]] || files+=("$real")
done
if [ ${#files[@]} -eq 0 ]; then
    echo "STOP: no .rptdesign files in $BIRT_DIR ${DESIGNS:-}" >&2
    exit 1
fi

changed=()
for f in "${files[@]}"; do
    n=$({ grep -o "$FROM" "$f" || true; } | wc -l)
    hosts=$({ grep -oE "https?://[A-Za-z0-9.-]+|jdbc:postgresql://[^/\"<]+/[A-Za-z0-9_]+" "$f" || true; } | sed 's|^\(jdbc:postgresql://\)[^@/]*@|\1|' | sort | uniq -c | tr '\n' ';' | sed 's/  */ /g')
    printf "%-44s %3s x %s -> %s   uses:%s\n" "$(basename "$f")" "$n" "$FROM" "$TO" "${hosts:- none}"
    if [ "$n" -gt 0 ]; then changed+=("$f"); fi
done
echo "(review the jdbc:postgresql hosts above: designs that read the database directly use those, not the app)"

if [ ${#changed[@]} -eq 0 ]; then
    echo "Nothing to change: no design points at $FROM."
    exit 0
fi
if [ "${2:-}" != "--apply" ]; then
    echo
    echo "Dry run: nothing changed. Run again with --apply to point ${#changed[@]} design(s) at $TO."
    exit 0
fi

backup=${BACKUP_DIR:-/root/birt-designs-backup-$(date +%Y%m%d-%H%M%S)}
mkdir -p "$backup"
for f in "${changed[@]}"; do
    cp --parents -p "$f" "$backup"
    sed "s/$(echo "$FROM" | sed 's/\./\\./g')/$TO/g" "$backup$f" > "$f"
done
echo "Done: ${#changed[@]} design(s) now use $TO. Backup: $backup"
echo "Now: sudo service tomcat7 restart"
