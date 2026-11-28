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
from avni.sync import household_checks, households
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
        voided = sum(1 for record in records if record.get("Voided"))
        duplicates.resolve(group, "{} voided, {} renumbered or moved".format(voided, len(records) - voided - len(live)))
        for external_id in group.external_ids:
            (context.duplicate_households or {}).pop(external_id, None)
        for record in sorted(records, key=lambda item: not item.get("Voided")):
            connector.sync_record("subject", record, context)
        counts["released"] = counts.get("released", 0) + release_held(group, context)
        counts["resolved"] += 1
    counts["encounters_closed"] = duplicates.recheck_encounters(PROVIDER)
    counts["possible_closed"] = household_checks.recheck()
    return counts


def release_held(group, context):
    """Sync every record that waited for this group, members first. Returns how many were synced."""
    held = (group.details or {}).get("held") or []
    order = ("subject", "enrolment", "encounter", "program_encounter")
    synced = 0
    for kind, external_id in sorted(held, key=lambda item: order.index(item[0]) if item[0] in order else len(order)):
        try:
            synced += int(bool(connector.sync_record(kind, context.provider.fetch(kind, external_id), context)))
        except Exception as exc:
            logger.warning("Held %s %s of duplicate %s not synced: %s", kind, external_id, group.key, exc)
    group.details = dict(group.details or {}, held=[])
    group.save(update_fields=["details"])
    return synced


def send_alerts(test_to=None):
    """Mail each city's team the programme work recorded on duplicate households since the last alert.
    Returns {city: records mailed}."""
    groups = [group for group in SyncDuplicate.objects.filter(provider=PROVIDER, kind=SyncDuplicate.HOUSEHOLD)
              .select_related("slum", "city__name") if (group.details or {}).get("alerts")]
    by_city, sent = {}, {}
    for group in groups:
        by_city.setdefault(city_of(group), []).append(group)
    for city_name, rows in sorted(by_city.items()):
        to, cc, bcc = contacts.recipients_for(purpose_key(city_name))
        if test_to:
            to, cc, bcc = [test_to], [], []
        if not to:
            logger.warning("Duplicate alerts for %s not mailed: no recipients on %s", city_name or "-", purpose_key(city_name))
            continue
        items = [dict(alert, slum=row.slum.name if row.slum_id else "", number=row.household_number,
                      ids=", ".join(row.external_ids)) for row in rows for alert in row.details["alerts"]]
        send_email(to, "{}Work recorded on duplicate households - {} ({})".format(
                       "[TEST] " if test_to else "", city_name or "no city", len(items)),
                   template_name="notification/duplicate_alert_email.html",
                   context={"city": city_name, "items": items}, cc=cc, bcc=bcc)
        if not test_to:
            for row in rows:
                details = dict(row.details)
                details["alerted"] = details.get("alerted", []) + details["alerts"]
                details["alerts"] = []
                row.details = details
                row.save(update_fields=["details"])
        sent[city_name] = len(items)
    return sent


def alert_step(from_date=None):
    """Nightly step: the alerts for work that landed on duplicate households tonight."""
    return send_alerts()


XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# What each kind means and what to do, in English and Marathi (mail, sheet "Read me", sheet names).
EXPLAIN = {
    SyncDuplicate.HOUSEHOLD: {
        "sheet": "Same number",
        "en": "Same household number used twice: two different households have the same number in one slum. "
              "Keep the right one; void the other, or give it its correct number or slum.",
        "mr": "एकच घर क्रमांक दोनदा: एका वस्तीत दोन वेगवेगळ्या घरांना एकच क्रमांक दिला आहे. योग्य घर ठेवा; "
              "दुसरे रद्द (void) करा किंवा त्याचा योग्य क्रमांक / वस्ती द्या.",
        "todo": "Void the wrong household, or renumber / move it",
    },
    SyncDuplicate.FAMILY: {
        "sheet": "Same family twice",
        "en": "Same family registered twice: the same head of household and mobile number appear under two household "
              "numbers. Check on the ground and void the extra registration.",
        "mr": "एकच कुटुंब दोनदा नोंदवले: एकाच कुटुंबप्रमुखाचे नाव व मोबाईल क्रमांक दोन घर क्रमांकांवर आहे. "
              "प्रत्यक्ष तपासा आणि जास्तीची नोंद रद्द (void) करा.",
        "todo": "Check which registration is right; void the extra one",
    },
    SyncDuplicate.NUMBER_AGAIN: {
        "sheet": "Number entered again",
        "en": "Household number entered again does not match: the number typed a second time is another household's "
              "number. Correct the household number.",
        "mr": "पुन्हा टाकलेला घर क्रमांक जुळत नाही: दुसऱ्यांदा टाकलेला क्रमांक दुसऱ्या घराचा आहे. घर क्रमांक दुरुस्त करा.",
        "todo": "Correct the household number (or the number entered again)",
    },
    SyncDuplicate.ENCOUNTER: {
        "sheet": "Visit twice",
        "en": "Visit entered twice: the same form for the same person or household on the same day. Void the extra one.",
        "mr": "एकच भेट दोनदा: एकाच दिवशी एकाच व्यक्ती / घरासाठी एकच फॉर्म दोनदा भरला आहे. जास्तीचा रद्द (void) करा.",
        "todo": "Void the extra visit",
    },
}
KIND_ORDER = (SyncDuplicate.HOUSEHOLD, SyncDuplicate.FAMILY, SyncDuplicate.NUMBER_AGAIN, SyncDuplicate.ENCOUNTER)
COLUMNS = ("City", "Slum", "Working slum this year", "Household number(s)", "Head of household", "Mobile",
           "Number entered again", "Visit type", "AVNI ids", "First seen", "New since last mail", "What to do in AVNI")


def city_of(row):
    return row.city.name.city_name if row.city_id else ""


def numbers_of(row):
    return ", ".join((row.details or {}).get("numbers") or ([row.household_number] if row.household_number else []))


def workbook(rows, city_name):
    """The groups as an .xlsx (filename, bytes, mimetype): a Read me sheet, then one sheet per kind."""
    import io
    from openpyxl import Workbook

    book = Workbook()
    readme = book.active
    readme.title = "Read me"
    readme.append(["Kind", "English", "मराठी", "Records"])
    for kind in KIND_ORDER:
        count = sum(1 for row in rows if row.kind == kind)
        if count:
            readme.append([EXPLAIN[kind]["sheet"], EXPLAIN[kind]["en"], EXPLAIN[kind]["mr"], count])
    for kind in KIND_ORDER:
        kind_rows = sorted((row for row in rows if row.kind == kind),
                           key=lambda row: (not (row.details or {}).get("working_slum"), row.slum.name if row.slum_id else ""))
        if not kind_rows:
            continue
        sheet = book.create_sheet(EXPLAIN[kind]["sheet"])
        sheet.append(COLUMNS)
        for row in kind_rows:
            details = row.details or {}
            sheet.append([city_of(row), row.slum.name if row.slum_id else "", "Yes" if details.get("working_slum") else "",
                          numbers_of(row), details.get("head", ""),
                          details.get("mobile", ""), details.get("entered_again", ""), row.encounter_type,
                          ", ".join(row.external_ids), row.first_seen.date(), "" if row.notified_on else "New",
                          EXPLAIN[kind]["todo"]])
    content = io.BytesIO()
    book.save(content)
    return ("duplicates_{}_{}.xlsx".format(slugify(city_name or "no-city"), timezone.localdate().isoformat()),
            content.getvalue(), XLSX)


def financial_year(day):
    start = day.year if day.month >= 4 else day.year - 1
    return "FY {}-{:02d}".format(start, (start + 1) % 100)


def send_digest(today=None, test_to=None):
    """Mail each city's team its open duplicates, details in an attached sheet; returns {city: groups mailed}.

    With `test_to`, every city's mail goes to that address only, marked [TEST], and nothing is marked notified."""
    sent = {}
    groups = SyncDuplicate.objects.filter(provider=PROVIDER, status=SyncDuplicate.OPEN, in_mail=True).select_related(
        "slum", "city__name").order_by("city_id", "kind", "slum__name", "household_number")
    by_city = {}
    for group in groups:
        by_city.setdefault(group.city.name.city_name if group.city_id else "", []).append(group)
    for city_name, rows in sorted(by_city.items()):
        to, cc, bcc = contacts.recipients_for(purpose_key(city_name))
        test_note = ""
        if test_to:
            test_note = "TEST - would go to: {}{}".format(", ".join(to) or "nobody yet", "; cc: " + ", ".join(cc) if cc else "")
            to, cc, bcc = [test_to], [], []
        if not to:
            logger.warning("Duplicates for %s not mailed: no recipients on %s", city_name or "-", purpose_key(city_name))
            continue
        first = not SyncDuplicate.objects.filter(
            provider=PROVIDER, city_id=rows[0].city_id, notified_on__isnull=False).exists()
        send_email(to, "{}Duplicate records in AVNI - {} ({} open)".format("[TEST] " if test_to else "", city_name or "no city", len(rows)),
                   template_name="notification/duplicate_digest_email.html",
                   context={"city": city_name, "kinds": [dict(EXPLAIN[kind], count=sum(1 for row in rows if row.kind == kind))
                                                          for kind in KIND_ORDER if any(row.kind == kind for row in rows)],
                            "new": sum(1 for row in rows if not row.notified_on), "first": first, "test_note": test_note,
                            "year": financial_year(timezone.localtime(today or timezone.now()).date())},
                   cc=cc, bcc=bcc, attachments=[workbook(rows, city_name)])
        if not test_to:
            SyncDuplicate.objects.filter(pk__in=[row.pk for row in rows]).update(notified_on=today or timezone.now())
        sent[city_name] = len(rows)
    return sent


def run(recorder, params=None):
    """Registry job duplicate_digest: weekly mail."""
    with recorder.step("duplicate_digest", loggers=LOGGERS) as step:
        if step.disabled:
            return
        send_digest(test_to=(params or {}).get("test_to"))
