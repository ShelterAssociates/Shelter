from master.models import City


def _user_city_names(user):
    group_names = user.groups.values_list("name", flat=True)
    return [name.split(":")[-1].strip() for name in group_names]


def can_access_rim_download(user):
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=["GIS", "Team Leader"]).exists()


def get_permitted_cities_for_rim(user):
    if user.is_superuser or user.groups.filter(name="GIS").exists():
        return City.objects.order_by("name__city_name")
    return City.objects.filter(
        name__city_name__in=_user_city_names(user)
    ).order_by("name__city_name")


def can_access_slum_for_rim(user, slum):
    if user.is_superuser or user.groups.filter(name="GIS").exists():
        return True
    return slum.has_permission(user)
