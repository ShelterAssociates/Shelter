#!/bin/bash
# Daily digest of every scheduled job run. Install as:
#
#0 6 * * * bash /srv/Shelter/deploy/JOB_DIGEST.sh

set -e

PROJECT_DIR="/srv/Shelter"
VENV_DIR="$PROJECT_DIR/ENV3"

export VIRTUAL_ENV="$VENV_DIR"
export PATH="$VENV_DIR/bin:$PATH"
export DJANGO_SETTINGS_MODULE=shelter.settings

cd "$PROJECT_DIR"

LOG_DIR="$HOME/sync_logs"
LOG_FILE="$LOG_DIR/job_digest.log"
MAX_SIZE=$((2 * 1024 * 1024))
mkdir -p "$LOG_DIR"

if [ -f "$LOG_FILE" ]; then
	CURRENT_SIZE=$(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)
	if [ "$CURRENT_SIZE" -ge "$MAX_SIZE" ]; then
		mv "$LOG_FILE" "${LOG_FILE}.1"
		touch "$LOG_FILE"
	fi
else
	touch "$LOG_FILE"
fi

exec >>"$LOG_FILE" 2>&1

trap 'echo "[ERROR] $(date "+%Y-%m-%d %H:%M:%S") - FAILED at line $LINENO running: $BASH_COMMAND"' ERR

echo "========== $(date "+%Y-%m-%d %H:%M:%S") : job digest starting =========="
"$VENV_DIR/bin/python" manage.py send_job_digest
echo "========== $(date "+%Y-%m-%d %H:%M:%S") : job digest finished =========="
