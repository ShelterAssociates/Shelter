cd /srv/Shelter/
source ENV/bin/activate
python manage.py shell <<ORM
from graphs.sync_avni_data import *
from time import sleep
import time
a = avni_sync()
# a.SaveDailyReportingdata()
# time.sleep(1m)
# a.SaveFamilyFactsheetData()
# time.sleep(1m)
# a.SaveCommunityMobilizationData()
# time.sleep(1m)
# a.SaveFollowupData()
# time.sleep(1m)
# a.SaveRhsData()
# time.sleep(1m)
# a.SaveWasteData()
# time.sleep(1m)
# a.SaveWaterData()
# time.sleep(1m)
# a.SaveElectricityData()
# time.sleep(1m)
# a.SavePropertyTaxData()
# time.sleep(1m)
# a.SaveDailyReportingdata()
a.sync_sanitation_data('/home/shelter/Desktop/Json_files_for_upload/sanitation_data_04_09_2025.json')
sleep(3)
a.sync_water_data('/home/shelter/Desktop/Json_files_for_upload/water_data_04_09_2025.json')
sleep(3)
a.sync_waste_data('/home/shelter/Desktop/Json_files_for_upload/waste_data_04_09_2025.json')
sleep(3)
a.sync_Electricity_data('/home/shelter/Desktop/Json_files_for_upload/electricity_data_04_09_2025.json')


ORM