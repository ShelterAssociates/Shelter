"""Slum name -> ids. Generic: no survey tool is involved."""


def slum_and_city_ids(slum_name):
    from master.models import Slum

    row = Slum.objects.filter(name=slum_name).values_list(
        "id", "electoral_ward_id__administrative_ward__city__id"
    ).first()
    if row is None:
        raise LookupError("No slum named '{}'".format(slum_name))
    return row[0], row[1]
