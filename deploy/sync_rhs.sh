#!/bin/bash
set -e

PROJECT_DIR="/srv/Shelter"
VENV_DIR="/srv/Shelter/ENV3"

export VIRTUAL_ENV="$VENV_DIR"
export PATH="$VENV_DIR/bin:$PATH"
export DJANGO_SETTINGS_MODULE=shelter.settings

echo "VIRTUAL_ENV=$VIRTUAL_ENV"
cd "$PROJECT_DIR"

SCRIPT_NAME="$(basename "$0")"

LOG_DIR="$HOME/sync_logs"
LOG_FILE="$LOG_DIR/rhs_sync.log"
MAX_SIZE=$((2 * 1024 * 1024))  # 2 MB

mkdir -p "$LOG_DIR"

# Rotate log if exceeds 2 MB
if [ -f "$LOG_FILE" ]; then
	CURRENT_SIZE=$(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)
	if [ "$CURRENT_SIZE" -ge "$MAX_SIZE" ]; then
		mv "$LOG_FILE" "${LOG_FILE}.1"
		touch "$LOG_FILE"
	fi
else
	touch "$LOG_FILE"
fi

usage() {
	echo
	echo "Usage: $SCRIPT_NAME [-h] [-i] [-d] MODE"
	echo
	echo "MODE:"
	echo "  1 = Household"
	echo "  2 = Structure"
	echo "  3 = IIDs"
	echo "  4 = Structure + Household (5 second delay)"
	echo
	echo "Options:"
	echo "  -i   Also print Cognito token"
	echo "  -d   Also print output to console (in addition to log file)"
	echo "  -h   Show help and exit"
	echo
	echo "Examples:"
	echo "  $SCRIPT_NAME 1"
	echo "  $SCRIPT_NAME -i 4"
	echo "  $SCRIPT_NAME -d 1"
	echo "  $SCRIPT_NAME -i -d 4"
	echo
}

PRINT_TOKEN=false
SHOW_HELP=false
PRINT_CONSOLE=false   # for -d

# Parse flags
while getopts ":hid" opt; do
	case "$opt" in
		h) SHOW_HELP=true ;;
		i) PRINT_TOKEN=true ;;
		d) PRINT_CONSOLE=true ;;
		\?)
			echo "Invalid option: -$OPTARG"
			SHOW_HELP=true
			;;
	esac
done
shift $((OPTIND - 1))

if $SHOW_HELP; then
	usage
	exit 0
fi

# Now decide logging behavior based on -d
if $PRINT_CONSOLE; then
	# Log + print to console
	exec > >(tee -a "$LOG_FILE") 2>&1
else
	# Log only, no console output
	exec >> "$LOG_FILE" 2>&1
fi

trap 'echo "[ERROR] $(date "+%Y-%m-%d %H:%M:%S") - Script FAILED at line $LINENO while running: $BASH_COMMAND"' ERR

MODE="${1:-}"

if [[ -z "$MODE" ]]; then
	echo "ERROR: MODE is required."
	usage
	exit 1
fi

case "$MODE" in
	1|2|3|4) ;;
	*)
		echo "ERROR: Invalid MODE: $MODE"
		usage
		exit 1
		;;
esac

echo "========== $(date "+%Y-%m-%d %H:%M:%S") : Starting RHS sync (mode=$MODE, print_token=$PRINT_TOKEN, print_console=$PRINT_CONSOLE) =========="
"$VENV_DIR/bin/python" manage.py shell <<EOF
from importlib import reload
import time
import graphs.sync_avni_data as sync_module

reload(sync_module)

mode = "$MODE"
print_token = "$PRINT_TOKEN".lower() in ("true", "1", "yes")

print(">>> Creating avni_sync object...")
a = sync_module.avni_sync()

print(">>> Mode:", mode)

if mode == "1":
    print(">>> Running Household Sync...")
    a.SaveRhsData("Household")

elif mode == "2":
    print(">>> Running Structure Sync...")
    a.SaveRhsData("Structure")

elif mode == "3":
    print(">>> Running Sync by IIDs...")
    a.SaveRhsData_byIIDs()

elif mode == "4":
    print(">>> Running Structure Sync (part 1 of 2)...")
    a.SaveRhsData("Structure")
    print(">>> Waiting 5 seconds before Household sync...")
    time.sleep(5)
    print(">>> Running Household Sync (part 2 of 2)...")
    a.SaveRhsData("Household")

else:
    print(">>> ERROR: Invalid mode received in Python:", mode)

if print_token:
    print(">>> Fetching Cognito token...")
    try:
        token = a.get_cognito_token()
        print("Cognito token:", token)
    except Exception as e:
        print("Failed to get Cognito token:", e)

EOF

echo "========== $(date "+%Y-%m-%d %H:%M:%S") : RHS sync finished =========="
