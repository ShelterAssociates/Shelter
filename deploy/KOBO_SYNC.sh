
cd /srv/Shelter/
source ENV3/bin/activate
python manage.py shell <<ORM
from deploy.RIM_SYNC import *
sync_kobo_data()
exit()
ORM

