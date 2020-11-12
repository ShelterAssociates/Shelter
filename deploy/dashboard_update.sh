cd /srv/Shelter/
source ENV/bin/activate
python manage.py shell <<ORM
from deploy.RIM_SYNC import *
update_cards()
exit()
ORM

