#!/bin/bash
# Nightly refresh of the cached AVNI form definitions the sync console validates
# uploads against. Reads metadata only. Install as a cron job:
#
#30 1 * * * bash /srv/Shelter/deploy/AVNI_FORM_CACHE_REFRESH.sh

set -e

PROJECT_DIR="/srv/Shelter"
VENV_DIR="$PROJECT_DIR/ENV3"

export VIRTUAL_ENV="$VENV_DIR"
export PATH="$VENV_DIR/bin:$PATH"
export DJANGO_SETTINGS_MODULE=shelter.settings

cd "$PROJECT_DIR"

LOG_DIR="$HOME/sync_logs"
LOG_FILE="$LOG_DIR/avni_form_cache.log"
MAX_SIZE=$((2 * 1024 * 1024))
mkdir -p "$LOG_DIR"

if [ -f "$LOG_FILE" ] && [ "$(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)" -ge "$MAX_SIZE" ]; then
	mv "$LOG_FILE" "${LOG_FILE}.1"
fi
touch "$LOG_FILE"

exec >>"$LOG_FILE" 2>&1

trap 'echo "[ERROR] $(date "+%Y-%m-%d %H:%M:%S") - FAILED at line $LINENO running: $BASH_COMMAND"' ERR

echo "========== $(date "+%Y-%m-%d %H:%M:%S") : AVNI form cache refresh starting =========="
"$VENV_DIR/bin/python" manage.py run_job avni_form_cache_refresh --trigger cron
echo "========== $(date "+%Y-%m-%d %H:%M:%S") : AVNI form cache refresh finished =========="
