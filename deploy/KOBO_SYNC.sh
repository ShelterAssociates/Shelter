#20 2-12 * * * bash /srv/Shelter/deploy/KOBO_SYNC.sh
#42 10 * * * bash /srv/Shelter/deploy/RIM_SYNC.sh
#0 23 * * * bash /srv/Shelter/deploy/dashboard_update.sh

cd /srv/Shelter/
source ENV3/bin/activate
python manage.py shell <<ORM
from deploy.RIM_SYNC import *
sync_kobo_data()
exit()
ORM

