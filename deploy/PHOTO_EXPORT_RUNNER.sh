#!/bin/bash
# Runs queued photo exports. Install as a cron job:
#
#*/2 * * * * bash /srv/Shelter/deploy/PHOTO_EXPORT_RUNNER.sh
#
# Runs one export per invocation and exits, so a long export can never stop the
# next tick from sweeping jobs orphaned by a deploy/restart. Overlapping ticks
# are safe: the runner claims work with SELECT ... FOR UPDATE SKIP LOCKED, so a
# second copy finds nothing to do rather than double-running a job.

set -e

PROJECT_DIR="/srv/Shelter"
VENV_DIR="$PROJECT_DIR/ENV3"

export VIRTUAL_ENV="$VENV_DIR"
export PATH="$VENV_DIR/bin:$PATH"
export DJANGO_SETTINGS_MODULE=shelter.settings

cd "$PROJECT_DIR"

LOG_DIR="$HOME/sync_logs"
LOG_FILE="$LOG_DIR/photo_export.log"
MAX_SIZE=$((2 * 1024 * 1024)) # 2 MB
mkdir -p "$LOG_DIR"

# Rotate log if it exceeds 2 MB (same idiom as sync_rhs.sh).
if [ -f "$LOG_FILE" ]; then
	CURRENT_SIZE=$(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)
	if [ "$CURRENT_SIZE" -ge "$MAX_SIZE" ]; then
		mv "$LOG_FILE" "${LOG_FILE}.1"
		touch "$LOG_FILE"
	fi
else
	touch "$LOG_FILE"
fi

exec >> "$LOG_FILE" 2>&1

trap 'echo "[ERROR] $(date "+%Y-%m-%d %H:%M:%S") - FAILED at line $LINENO running: $BASH_COMMAND"' ERR

echo "========== $(date "+%Y-%m-%d %H:%M:%S") : photo export runner starting =========="
"$VENV_DIR/bin/python" manage.py run_photo_exports
echo "========== $(date "+%Y-%m-%d %H:%M:%S") : photo export runner finished =========="
