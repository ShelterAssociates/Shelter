"""Duplicate households and visits: the nightly re-check, and the weekly mail to each city's team.

Open household groups are re-read from AVNI by id every night (a few GETs). When
AVNI no longer has two live households with that slum and number - one voided,
renumbered or moved - every household in the group is synced again, so the
survivor gets its row, and the group is closed. Encounter groups close once only
one live visit is left. Each city's team gets the open groups once a week, at the
addresses on its mail purpose `duplicates-<city>` (to / cc set in the address book).
"""

import logging

from django.template.defaultfilters import slugify
from django.utils import timezone

from avni.client import AvniError
from avni.sync import households
from helpers.services.send_email import send_email
from notification.services import contacts
from survey import connector, duplicates
from survey.models import SyncDuplicate

logger = logging.getLogger(__name__)

PROVIDER = "avni"
LOGGERS = ["avni.jobs.duplicates", "survey.duplicates"]


def purpose_key(city_name):
    return "duplicates-{}".format(slugify(city_name or "no-city"))


def still_colliding(records, slum_id, number, context):
    """Ids of the live households that still share this slum and number."""
    live = []
    for record in records:
        household = households.household_from_record(record)
        if record.get("Voided") or household.number != number:
            continue
        if connector.store.resolve_slum(household.slum, context)[0] == slum_id:
            live.append(record["ID"])
    return live


def recheck(from_date=None, context=None):
    """Close the groups AVNI has resolved and sync their households again. Returns counts."""
    from avni.provider import sync_context

    context = context or sync_context()
    counts = {"open": 0, "resolved": 0}
    for group in SyncDuplicate.objects.filter(provider=PROVIDER, kind=SyncDuplicate.HOUSEHOLD, status=SyncDuplicate.OPEN):
        records = []
        for uuid in group.external_ids:
            try:
                records.append(context.provider.get_subject(uuid))
            except AvniError as exc:
                logger.warning("Duplicate %s: subject %s not read: %s", group.key, uuid, exc)
        live = still_colliding(records, group.slum_id, group.household_number, context)
        if len(live) > 1 or len(records) < len(group.external_ids):
            counts["open"] += 1
            continue
        for record in sorted(records, key=lambda item: not item.get("Voided")):
            connector.sync_record("subject", record, context)
        voided = sum(1 for record in records if record.get("Voided"))
        duplicates.resolve(group, "{} voided, {} renumbered or moved".format(voided, len(records) - voided - len(live)))
        counts["resolved"] += 1
    counts["encounters_closed"] = duplicates.recheck_encounters(PROVIDER)
    return counts


SHEET_COLUMNS = ("Kind", "City", "Slum", "Household number", "Visit type", "AVNI ids", "First seen", "Last seen",
                 "New since last mail", "What to do in AVNI")
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def todo(group):
    if group.kind == SyncDuplicate.HOUSEHOLD:
        return "{} households share number {}: void the wrong one, or renumber / move it".format(
            len(group.external_ids), group.household_number)
    return "{} {} visits on one day: void the extra one".format(len(group.external_ids), group.encounter_type)


def workbook(rows, city_name):
    """The open groups as an .xlsx attachment (filename, bytes, mimetype)."""
    import io
    from openpyxl import Workbook

    book = Workbook()
    sheet = book.active
    sheet.title = "Duplicates"
    sheet.append(SHEET_COLUMNS)
    for row in rows:
        sheet.append([row.get_kind_display(), city_name, row.slum.name if row.slum_id else "", row.household_number,
                      row.encounter_type, ", ".join(row.external_ids), row.first_seen.date(), row.last_seen.date(),
                      "" if row.notified_on else "New", todo(row)])
    content = io.BytesIO()
    book.save(content)
    return ("duplicates_{}_{}.xlsx".format(slugify(city_name or "no-city"), timezone.localdate().isoformat()),
            content.getvalue(), XLSX)


def send_digest(today=None):
    """Mail each city's team its open duplicates, details in an attached sheet; returns {city: groups mailed}."""
    sent = {}
    groups = SyncDuplicate.objects.filter(provider=PROVIDER, status=SyncDuplicate.OPEN).select_related(
        "slum", "city__name").order_by("city_id", "kind", "slum__name", "household_number")
    by_city = {}
    for group in groups:
        by_city.setdefault(group.city.name.city_name if group.city_id else "", []).append(group)
    for city_name, rows in sorted(by_city.items()):
        to, cc, bcc = contacts.recipients_for(purpose_key(city_name))
        if not to:
            logger.warning("Duplicates for %s not mailed: no recipients on %s", city_name or "-", purpose_key(city_name))
            continue
        households = [row for row in rows if row.kind == SyncDuplicate.HOUSEHOLD]
        send_email(to, "Duplicate records in AVNI - {} ({} open)".format(city_name or "no city", len(rows)),
                   template_name="notification/duplicate_digest_email.html",
                   context={"city": city_name, "households": len(households), "visits": len(rows) - len(households),
                            "new": sum(1 for row in rows if not row.notified_on)},
                   cc=cc, bcc=bcc, attachments=[workbook(rows, city_name)])
        SyncDuplicate.objects.filter(pk__in=[row.pk for row in rows]).update(notified_on=today or timezone.now())
        sent[city_name] = len(rows)
    return sent


def run(recorder, params=None):
    """Registry job duplicate_digest: weekly mail."""
    with recorder.step("duplicate_digest", loggers=LOGGERS) as step:
        if step.disabled:
            return
        send_digest()
