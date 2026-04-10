#!/usr/bin/env bash
set -e

# Must have exactly 2 arguments
if [ $# -ne 2 ]; then
    echo "Please provide exactly TWO arguments (1 or 2)"
    echo "1 for Production Environment and 2 for Local Environment at First Argument"
    echo "1 for Syncing Encounter Data and 2 for Syncing Member Data at Second Argument"
    exit 1
fi

ENV_CHOICE="$1"
DATA_CHOICE="$2"

########################################
# 1) Activate environment + go to project root
########################################

if [ "$ENV_CHOICE" = "1" ]; then
    echo "Activating Production Environment"
    cd /srv/Shelter/ || exit 1
    source ENV3/bin/activate

elif [ "$ENV_CHOICE" = "2" ]; then
    echo "Activating Local Environment"
    cd "$HOME/Desktop/Shelter_New" || exit 1
    # activate your local env here if needed, e.g.:
    # conda activate pyenv36
else
    echo "Invalid first argument. Please provide either 1 (Production) or 2 (Local)."
    exit 1
fi

echo "Project root: $(pwd)"

########################################
# 2) Build date-based paths
########################################

# For encounter data files: DD_MM_YYYY (e.g. 08_12_2025)
TODAY_DMY=$(date +%d_%m_%Y)

# For member data files: YYYY-MM-DD (e.g. 2025-12-08)
TODAY_YMD=$(date +%F)

ENCOUNTER_DIR="$HOME/data_for_sync/encounter_data_upload"
MEMBER_DIR="$HOME/data_for_sync/member_data_upload"

ELECTRICITY_PATH="$ENCOUNTER_DIR/electricity_data_${TODAY_DMY}.json"
SANITATION_PATH="$ENCOUNTER_DIR/sanitation_data_${TODAY_DMY}.json"
WASTE_PATH="$ENCOUNTER_DIR/waste_data_${TODAY_DMY}.json"
WATER_PATH="$ENCOUNTER_DIR/water_data_${TODAY_DMY}.json"

MEMBER_PATH="$MEMBER_DIR/member_${TODAY_YMD}.json"
PROGRAM_PATH="$MEMBER_DIR/family_member_menstral_hygine_program_data_${TODAY_YMD}.json"
ENCOUNTER_MEMBER_PATH="$MEMBER_DIR/family_member_menstrual_hygiene_followup_data_${TODAY_YMD}.json"

########################################
# 3) Decide what to sync
########################################

if [ "$DATA_CHOICE" = "1" ]; then
    echo "Syncing Encounter Data"

    python manage.py shell <<ORM
from graphs.sync_avni_data import *
from time import sleep
import time

a = avni_sync()

electricity_path = "$ELECTRICITY_PATH"
sanitation_path = "$SANITATION_PATH"
waste_path = "$WASTE_PATH"
water_path = "$WATER_PATH"

a.sync_sanitation_data(sanitation_path)
print("Sanitation data synced. Waiting for 5 seconds before next sync...")
sleep(5)

a.sync_water_data(water_path)
print("Water data synced. Waiting for 5 seconds before next sync...")
sleep(5)

a.sync_waste_data(waste_path)
print("Waste data synced. Waiting for 5 seconds before next sync...")
sleep(5)

a.sync_Electricity_data(electricity_path)
print("Electricity data synced.")
ORM
    exit 0

elif [ "$DATA_CHOICE" = "2" ]; then
    echo "Syncing Member Data"

    python manage.py shell <<ORM
from graphs.sync_avni_data import *
from time import sleep
import time

a = avni_sync()

member_path = "$MEMBER_PATH"
program_path = "$PROGRAM_PATH"
encounter_path = "$ENCOUNTER_MEMBER_PATH"

a.SaveMemberData(member_path)
print("Member data synced. Waiting for 5 seconds before next sync...")
sleep(5)

a.SaveMemberProgramData(program_path)
print("Member Program data synced. Waiting for 5 seconds before next sync...")
sleep(5)

a.SaveMemberEncounterData(encounter_path)
print("Member Encounter data synced.")
ORM
    exit 0

else
    echo "Invalid second argument. Please provide either 1 (Sync Encounter Data) or 2 (Sync Member Data)."
    exit 1
fi
