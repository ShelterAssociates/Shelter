#!/bin/bash
# Manual RHS (household / structure registration) sync from AVNI.
# Runs through manage.py run_job so the run is recorded and reported like cron jobs.
#
#   sync_rhs.sh [-d] [-f YYYY-MM-DD] MODE
#     MODE 1 = Household, 2 = Structure, 4 = Structure + Household
#     -f     sync everything modified since this date (default: newest local record - 1 day)
#     -d     also print to console
#
# Single records by uuid: python manage.py shell -c
#   "from avni.sync.by_uuid import sync_by_uuid; sync_by_uuid('subject', ['<uuid>'])"
set -e

PROJECT_DIR="/srv/Shelter"
VENV_DIR="$PROJECT_DIR/ENV3"
export VIRTUAL_ENV="$VENV_DIR"
export PATH="$VENV_DIR/bin:$PATH"
export DJANGO_SETTINGS_MODULE=shelter.settings
cd "$PROJECT_DIR"

LOG_DIR="$HOME/sync_logs"
LOG_FILE="$LOG_DIR/rhs_sync.log"
MAX_SIZE=$((2 * 1024 * 1024))
mkdir -p "$LOG_DIR"
if [ -f "$LOG_FILE" ] && [ "$(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)" -ge "$MAX_SIZE" ]; then
	mv "$LOG_FILE" "${LOG_FILE}.1"
fi
touch "$LOG_FILE"

usage() {
	sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'
}

PRINT_CONSOLE=false
FROM_DATE=""
while getopts ":hdf:" opt; do
	case "$opt" in
		h) usage; exit 0 ;;
		d) PRINT_CONSOLE=true ;;
		f) FROM_DATE="$OPTARG" ;;
		\?) echo "Invalid option: -$OPTARG"; usage; exit 1 ;;
	esac
done
shift $((OPTIND - 1))

case "${1:-}" in
	1) SUBJECT_TYPES='["Household"]' ;;
	2) SUBJECT_TYPES='["Structure"]' ;;
	4) SUBJECT_TYPES='["Structure", "Household"]' ;;
	*) echo "ERROR: MODE must be 1, 2 or 4."; usage; exit 1 ;;
esac

if $PRINT_CONSOLE; then
	exec > >(tee -a "$LOG_FILE") 2>&1
else
	exec >> "$LOG_FILE" 2>&1
fi
trap 'echo "[ERROR] $(date "+%Y-%m-%d %H:%M:%S") - FAILED at line $LINENO running: $BASH_COMMAND"' ERR

PARAMS="{\"subject_types\": $SUBJECT_TYPES"
if [ -n "$FROM_DATE" ]; then
	PARAMS="$PARAMS, \"from_date\": \"$FROM_DATE\""
fi
PARAMS="$PARAMS}"

echo "========== $(date "+%Y-%m-%d %H:%M:%S") : RHS sync starting (params=$PARAMS) =========="
"$VENV_DIR/bin/python" manage.py run_job rhs_sync --trigger manual --params "$PARAMS"
echo "========== $(date "+%Y-%m-%d %H:%M:%S") : RHS sync finished =========="
