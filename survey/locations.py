"""Slum lookups. Generic: no survey tool is involved."""


def slum_and_city_ids(slum_name):
    from master.models import Slum

    row = Slum.objects.filter(name=slum_name).values_list(
        "id", "electoral_ward_id__administrative_ward__city__id"
    ).first()
    if row is None:
        raise LookupError("No slum named '{}'".format(slum_name))
    return row[0], row[1]


def slum_external_id(provider, slum_id):
    """The provider's id for a slum, or None when the slum has no alias there."""
    from survey.models import SlumAlias

    return SlumAlias.objects.filter(provider=provider, slum_id=slum_id).values_list("external_id", flat=True).first()


def slum_ids_for(provider):
    """Sorted ids of every slum the provider knows."""
    from survey.models import SlumAlias

    return sorted(SlumAlias.objects.filter(provider=provider).values_list("slum_id", flat=True))


def slum_id_for_external_id(provider, external_id):
    """Slum id for a provider's id, or None when nothing is mapped to it."""
    from survey.models import SlumAlias

    if not external_id:
        return None
    return SlumAlias.objects.filter(provider=provider, external_id=external_id).values_list("slum_id", flat=True).first()
