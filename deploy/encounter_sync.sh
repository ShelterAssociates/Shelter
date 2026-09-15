#!/usr/bin/env bash
# Import AVNI JSON exports placed under ~/data_for_sync (manual, developer-run).
# Each file is imported through manage.py run_job file_import so the run is recorded.
#
#   encounter_sync.sh ENV DATA
#     ENV  1 = production (/srv/Shelter), 2 = local (~/Shelter/app)
#     DATA 1 = encounter files (sanitation, water, waste, electricity)
#          2 = member files (members, programs, encounters)
set -e

if [ $# -ne 2 ]; then
	sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'
	exit 1
fi

case "$1" in
	1) cd /srv/Shelter || exit 1; PYTHON="/srv/Shelter/ENV3/bin/python" ;;
	2) cd "$HOME/Shelter/app" || exit 1; PYTHON="python" ;;
	*) echo "ENV must be 1 (production) or 2 (local)"; exit 1 ;;
esac
echo "Project root: $(pwd)"

TODAY_DMY=$(date +%d_%m_%Y)
TODAY_YMD=$(date +%F)
ENCOUNTER_DIR="$HOME/data_for_sync/encounter_data_upload"
MEMBER_DIR="$HOME/data_for_sync/member_data_upload"

import_file() {
	local kind="$1" path="$2"
	if [ ! -f "$path" ]; then
		echo "Skipping $kind: $path not found"
		return
	fi
	echo "Importing $kind from $path"
	"$PYTHON" manage.py run_job file_import --trigger manual --params "{\"kind\": \"$kind\", \"path\": \"$path\"}"
	sleep 5
}

case "$2" in
	1)
		import_file sanitation "$ENCOUNTER_DIR/sanitation_data_${TODAY_DMY}.json"
		import_file water "$ENCOUNTER_DIR/water_data_${TODAY_DMY}.json"
		import_file waste "$ENCOUNTER_DIR/waste_data_${TODAY_DMY}.json"
		import_file electricity "$ENCOUNTER_DIR/electricity_data_${TODAY_DMY}.json"
		;;
	2)
		import_file members "$MEMBER_DIR/member_${TODAY_YMD}.json"
		import_file member_programs "$MEMBER_DIR/family_member_menstral_hygine_program_data_${TODAY_YMD}.json"
		import_file member_encounters "$MEMBER_DIR/family_member_menstrual_hygiene_followup_data_${TODAY_YMD}.json"
		;;
	*) echo "DATA must be 1 (encounters) or 2 (members)"; exit 1 ;;
esac
