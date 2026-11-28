"""Records the provider holds twice (survey.models.SyncDuplicate). Generic: no survey tool is involved."""

from django.utils import timezone

from survey.models import Record, SyncDuplicate

ENCOUNTER_KINDS = ("encounter", "program_encounter")


def remember(provider, kind, key, external_ids, **fields):
    """Open (or reopen) the group under `key` and add these ids to it."""
    now = timezone.now()
    duplicate, created = SyncDuplicate.objects.get_or_create(
        provider=provider, kind=kind, key=key, defaults=dict(fields, external_ids=sorted(set(external_ids))))
    if not created:
        duplicate.external_ids = sorted(set(duplicate.external_ids or []) | set(external_ids))
        duplicate.last_seen = now
        if duplicate.status == SyncDuplicate.RESOLVED:
            duplicate.status, duplicate.resolved_on, duplicate.resolution = SyncDuplicate.OPEN, None, ""
        for name, value in fields.items():
            setattr(duplicate, name, value)
        duplicate.save()
    return duplicate


def household_key(slum_id, number):
    return "{}:{}".format(slum_id, number)


def remember_household(provider, slum_id, city_id, number, external_ids):
    return remember(provider, SyncDuplicate.HOUSEHOLD, household_key(slum_id, number), external_ids,
                    slum_id=slum_id, city_id=city_id, household_number=number)


def flag_encounter(provider, external_id):
    """Flag the stored encounter when another live one has its subject, type and day. Returns the group or None."""
    record = Record.objects.filter(provider=provider, external_id=external_id).order_by("-version").first()
    if record is None or record.kind not in ENCOUNTER_KINDS or record.is_voided or not record.record_datetime:
        return None
    day = timezone.localtime(record.record_datetime).date() if timezone.is_aware(record.record_datetime) else record.record_datetime.date()
    twins = list(twin_ids(record, day))
    if len(twins) < 2:
        return None
    key = "{}:{}:{}".format(record.subject_external_id, record.encounter_type, day.isoformat())
    return remember(provider, SyncDuplicate.ENCOUNTER, key, twins, slum_id=record.slum_id, city_id=record.city_id,
                    household_number=record.household_number, encounter_type=record.encounter_type)


def twin_ids(record, day):
    same = Record.objects.filter(
        provider=record.provider, kind=record.kind, subject_external_id=record.subject_external_id,
        encounter_type=record.encounter_type, is_voided=False, record_datetime__date=day,
    )
    return set(same.values_list("external_id", flat=True))


def resolve(duplicate, resolution):
    duplicate.status, duplicate.resolved_on, duplicate.resolution = SyncDuplicate.RESOLVED, timezone.now(), resolution
    duplicate.save(update_fields=["status", "resolved_on", "resolution"])


def recheck_encounters(provider):
    """Close encounter groups that no longer have two live records. Returns how many closed."""
    closed = 0
    for duplicate in SyncDuplicate.objects.filter(provider=provider, kind=SyncDuplicate.ENCOUNTER, status=SyncDuplicate.OPEN):
        live = Record.objects.filter(provider=provider, external_id__in=duplicate.external_ids, is_voided=False)
        if live.values("external_id").distinct().count() < 2:
            resolve(duplicate, "only one left after voids")
            closed += 1
    return closed


def flag_stored_encounters(provider):
    """Scan the whole store for encounters entered twice (offline; for existing data). Returns groups flagged."""
    flagged = set()
    rows = (Record.objects.filter(provider=provider, kind__in=ENCOUNTER_KINDS, is_voided=False)
            .exclude(record_datetime__isnull=True).exclude(subject_external_id="")
            .values_list("external_id", "kind", "subject_external_id", "encounter_type", "record_datetime"))
    seen = {}
    for external_id, kind, subject, encounter_type, moment in rows.iterator():
        day = timezone.localtime(moment).date() if timezone.is_aware(moment) else moment.date()
        group = (kind, subject, encounter_type, day)
        if group in seen and seen[group] != external_id:
            duplicate = flag_encounter(provider, external_id)
            if duplicate is not None:
                flagged.add(duplicate.pk)
        seen.setdefault(group, external_id)
    return len(flagged)
