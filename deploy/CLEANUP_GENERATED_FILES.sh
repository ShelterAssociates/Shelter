#!/bin/bash
# Deletes generated export files older than the retention window. Install as:
#
#0 5 * * * bash /srv/Shelter/deploy/CLEANUP_GENERATED_FILES.sh
#
# 05:00 is clear of the 23:00 dashboard job and the nightly Avni sync.
#
# ---------------------------------------------------------------------------
# THIS SCRIPT ONLY EVER TOUCHES THE THREE EXPORT DIRECTORIES LISTED BELOW.
#
# It is an allowlist, not a sweep of media/. Everything else under media/ is
# either a user upload or referenced from the database, and deleting any of it
# would cause real data loss:
#
#   media/FFReport/        BIRT family factsheet zips -- KEPT PERMANENTLY.
#                          Also referenced by SponsorProjectDetailsSubFields
#                          .zip_file, so deleting them breaks DB rows too.
#   media/ShelterPhotos/   user-uploaded photos
#   media/slum_transformation/, media/sponsor_project(s)/, icon dirs
#                          all backed by FileField/ImageField columns
#   media/shelter/attachments/
#                          the KoboToolbox photo backup -- irreplaceable
#
# Do not add a directory here without checking nothing in the database points
# into it.
# ---------------------------------------------------------------------------
#
# Dry run (prints what it would delete, removes nothing):
#   bash deploy/CLEANUP_GENERATED_FILES.sh --dry-run

set -e

PROJECT_DIR="/srv/Shelter"


MEDIA_DIR="${SHELTER_MEDIA_DIR:-$(dirname "$PROJECT_DIR")/media}"

# Retention in minutes. 1440 = 24 hours, matching the expiry note in the
# "export ready" emails.
RETENTION_MINUTES=1440

# The ONLY directories this script may delete from, relative to MEDIA_DIR.
EXPORT_DIRS=("photo_exports" "gis_exports" "rim_exports")

DRY_RUN=false
if [ "$1" = "--dry-run" ]; then
	DRY_RUN=true
fi

LOG_DIR="$HOME/sync_logs"
LOG_FILE="$LOG_DIR/cleanup_generated_files.log"
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

if $DRY_RUN; then
	exec > >(tee -a "$LOG_FILE") 2>&1
else
	exec >> "$LOG_FILE" 2>&1
fi

trap 'echo "[ERROR] $(date "+%Y-%m-%d %H:%M:%S") - FAILED at line $LINENO running: $BASH_COMMAND"' ERR

echo "========== $(date "+%Y-%m-%d %H:%M:%S") : cleanup starting =========="

if [ ! -d "$MEDIA_DIR" ]; then
	echo "[ERROR] Media directory $MEDIA_DIR does not exist."
	echo "        Nothing was cleaned. Check the path (MEDIA_ROOT = PARENT_DIR/media)"
	echo "        or set SHELTER_MEDIA_DIR to the correct location."
	exit 1
fi
echo "Media directory: $MEDIA_DIR"

BEFORE_KB=$(df -Pk "$MEDIA_DIR" | awk 'NR==2 {print $4}')
TOTAL_REMOVED=0

for NAME in "${EXPORT_DIRS[@]}"; do
	TARGET="$MEDIA_DIR/$NAME"

	# Refuse anything that isn't a real directory directly under media/.
	case "$TARGET" in
	"$MEDIA_DIR"/*) ;;
	*)
		echo "REFUSING $TARGET -- outside $MEDIA_DIR"
		continue
		;;
	esac

	if [ ! -d "$TARGET" ]; then
		echo "  $NAME: not present, skipping"
		continue
	fi

	COUNT=$(find "$TARGET" -mindepth 1 -maxdepth 1 -type d -mmin "+$RETENTION_MINUTES" 2>/dev/null | wc -l)
	if [ "$COUNT" -eq 0 ]; then
		echo "  $NAME: nothing older than ${RETENTION_MINUTES}m"
		continue
	fi

	if $DRY_RUN; then
		echo "  $NAME: would remove $COUNT export dir(s):"
		find "$TARGET" -mindepth 1 -maxdepth 1 -type d -mmin "+$RETENTION_MINUTES" -printf "      %p\n" 2>/dev/null
	else
		# -mindepth 1 so the export directory itself is never removed.
		find "$TARGET" -mindepth 1 -maxdepth 1 -type d -mmin "+$RETENTION_MINUTES" \
			-exec rm -rf {} + 2>/dev/null
		echo "  $NAME: removed $COUNT export dir(s)"
	fi
	TOTAL_REMOVED=$((TOTAL_REMOVED + COUNT))
done

AFTER_KB=$(df -Pk "$MEDIA_DIR" | awk 'NR==2 {print $4}')
RECLAIMED_MB=$(((AFTER_KB - BEFORE_KB) / 1024))

echo "Removed $TOTAL_REMOVED export dir(s); free space change: ${RECLAIMED_MB} MB"
echo "Free space now: $(df -Ph "$MEDIA_DIR" | awk 'NR==2 {print $4" of "$2" ("$5" used)"}')"
echo "========== $(date "+%Y-%m-%d %H:%M:%S") : cleanup finished =========="
