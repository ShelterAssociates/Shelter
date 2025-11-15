cd /srv/Shelter/
source ENV3/bin/activate
python manage.py shell <<ORM
from graphs.sync_avni_data import *
from time import sleep
import time
a = avni_sync()
a.SaveDailyReportingdata()
time.sleep(1)
a.SaveFamilyFactsheetData()
time.sleep(1)
a.SaveCommunityMobilizationData()
time.sleep(1)
## Not Doing currently
# a.SaveFollowupData()
# time.sleep(1m)
# a.SaveRhsData('Household')
# time.sleep(1m)
# a.SaveRhsData('Structure')
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
#a.sync_sanitation_data('/home/ubuntu/Json_files_for_upload/sanitation_data_09_10_2025.json')
#sleep(3)
#a.sync_water_data('/home/ubuntu/Json_files_for_upload/water_data_09_10_2025.json')
#sleep(3)
#a.sync_waste_data('/home/ubuntu/Json_files_for_upload/waste_data_09_10_2025.json')
#sleep(3)
#a.sync_Electricity_data('/home/ubuntu/Json_files_for_upload/electricity_data_09_10_2025.json')


ORM

sudo bash /srv/Shelter/deploy/auto_ssl_renew.sh

