#20 2-12 * * * bash /srv/Shelter/deploy/KOBO_SYNC.sh
#42 10 * * * bash /srv/Shelter/deploy/RIM_SYNC.sh
#0 23 * * * bash /srv/Shelter/deploy/dashboard_update.sh

cd /srv/Shelter/
source ENV3/bin/activate
python manage.py shell <<ORM
from graphs.dashboard_card import dashboard_data_Save
from master.models import City

# Only cities with real survey data / an active dashboard -- not every City
# row (several are administrative-boundary-only or not yet onboarded).
ACTIVE_CITY_NAMES = [
    "Kolhapur",
    "Thane",
    "Navi Mumbai",
    "Pune",
    "Panvel",
    "PCMC",
]

for city in City.objects.filter(name__city_name__in=ACTIVE_CITY_NAMES):
    try:
        dashboard_data_Save(city.id)
    except Exception as e:
        print(f"dashboard_data_Save failed for city {city.id} ({city.name.city_name}): {e}")
exit()
ORM

