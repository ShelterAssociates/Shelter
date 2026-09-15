#!/bin/bash
# Nightly Avni sync. Install as a cron job:
#
#0 22 * * * bash /srv/Shelter/deploy/AVNI_DAILY_SYNC.sh
#
# Steps: RHS Household registration, Daily Reporting, Family Factsheet,
# Community Mobilization (see avni/jobs/daily_sync.py). Every step is
# recorded in Django admin (Job runs) and emailed on failure.
# dashboard_update.sh is NO LONGER chained here -- it runs fortnightly on its
# own cron line (1st and 16th). Chaining it made it run nightly.
# sync_rhs.sh remains for manual Structure / by-IID runs only.

set -e

PROJECT_DIR="/srv/Shelter"
VENV_DIR="$PROJECT_DIR/ENV3"

export VIRTUAL_ENV="$VENV_DIR"
export PATH="$VENV_DIR/bin:$PATH"
export DJANGO_SETTINGS_MODULE=shelter.settings

cd "$PROJECT_DIR"

LOG_DIR="$HOME/sync_logs"
LOG_FILE="$LOG_DIR/avni_daily_sync.log"
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

echo "========== $(date "+%Y-%m-%d %H:%M:%S") : avni daily sync starting =========="
"$VENV_DIR/bin/python" manage.py run_job avni_daily_sync --trigger cron
echo "========== $(date "+%Y-%m-%d %H:%M:%S") : avni daily sync finished =========="

sudo bash /srv/Shelter/deploy/auto_ssl_renew.sh
