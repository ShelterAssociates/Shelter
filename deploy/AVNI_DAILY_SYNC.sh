cd /srv/Shelter/
source ENV/bin/activate
python manage.py shell <<ORM
from graphs.sync_avni_data import *
import time
a = avni_sync()
a.SaveDailyReportingdata()
time.sleep(1m)
a.SaveFamilyFactsheetData()
time.sleep(1m)
a.SaveCommunityMobilizationData()
time.sleep(1m)
a.SaveFollowupData()
time.sleep(1m)
a.SaveRhsData()
time.sleep(1m)
a.SaveWasteData()
time.sleep(1m)
a.SaveWaterData()
time.sleep(1m)
a.SaveElectricityData()
time.sleep(1m)
a.SavePropertyTaxData()
time.sleep(1m)
a.SaveDailyReportingdata()
ORM