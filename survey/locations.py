"""Slum lookups. Generic: no survey tool is involved."""


def slum_and_city_ids(slum_name, provider=None):
    """(slum id, city id) for a location title, or LookupError.

    An alias title wins over the Slum name, so a re-surveyed slum's second
    location feeds the slum its alias points at.
    """
    from master.models import Slum

    slum_id = slum_id_for_title(slum_name, provider)
    rows = Slum.objects.filter(id=slum_id) if slum_id else Slum.objects.filter(name=slum_name)
    row = rows.values_list("id", "electoral_ward_id__administrative_ward__city__id").first()
    if row is None:
        raise LookupError("No slum named '{}'".format(slum_name))
    return row[0], row[1]


def slum_id_for_title(slum_name, provider=None):
    """Slum id of the alias carrying this location title, or None."""
    from survey.models import SlumAlias

    if not slum_name:
        return None
    aliases = SlumAlias.objects.filter(external_name=slum_name)
    if provider:
        aliases = aliases.filter(provider=provider)
    return aliases.values_list("slum_id", flat=True).first()


def slum_id_for_name(slum_name, provider=None):
    """Slum id for a location title, or None. An alias title wins over the Slum name."""
    from master.models import Slum

    if not slum_name:
        return None
    return (
        slum_id_for_title(slum_name, provider)
        or Slum.objects.filter(name=slum_name).values_list("id", flat=True).first()
    )


def slum_external_id(provider, slum_id):
    """The provider's primary id for a slum, or None when the slum has no alias there."""
    from survey.models import SlumAlias

    return (
        SlumAlias.objects.filter(provider=provider, slum_id=slum_id, is_primary=True)
        .values_list("external_id", flat=True)
        .first()
    )


def slum_external_ids(provider, slum_id):
    """Every id the provider has for a slum, primary first."""
    from survey.models import SlumAlias

    return list(
        SlumAlias.objects.filter(provider=provider, slum_id=slum_id)
        .order_by("-is_primary", "external_id")
        .values_list("external_id", flat=True)
    )


def slum_ids_for(provider):
    """Sorted ids of every slum the provider knows."""
    from survey.models import SlumAlias

    return sorted(set(SlumAlias.objects.filter(provider=provider).values_list("slum_id", flat=True)))


def slum_id_for_external_id(provider, external_id):
    """Slum id for a provider's id, or None when nothing is mapped to it."""
    from survey.models import SlumAlias

    if not external_id:
        return None
    return SlumAlias.objects.filter(provider=provider, external_id=external_id).values_list("slum_id", flat=True).first()
