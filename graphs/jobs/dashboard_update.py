"""The nightly dashboard rebuild, previously a heredoc in
deploy/dashboard_update.sh. City list and behaviour are unchanged.
"""

from notification.services import reporting

LOGGERS = ["graphs.dashboard_card"]

# Only cities with real survey data / an active dashboard -- not every City row.
ACTIVE_CITY_NAMES = [
    "Kolhapur",
    "Thane",
    "Navi Mumbai",
    "Pune",
    "Panvel",
    "PCMC",
]


def run(recorder, params=None):
    from graphs.dashboard_card import dashboard_data_Save
    from master.models import City

    cities = City.objects.filter(name__city_name__in=ACTIVE_CITY_NAMES)
    city_ids = (params or {}).get("city_ids")
    if city_ids:
        cities = cities.filter(id__in=city_ids)
    cities = list(cities)
    with recorder.step("dashboard_data_Save", loggers=LOGGERS) as step:
        if step.disabled:
            return
        step.expect(len(cities))
        for city in cities:
            with reporting.record(city=city.name.city_name, city_id=city.id) as item:
                try:
                    dashboard_data_Save(city.id)
                except Exception as exc:
                    if item is not None:
                        item.mark_failed("{}: {}".format(type(exc).__name__, exc))
