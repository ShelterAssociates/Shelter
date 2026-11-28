"""Put household numbers back on members from an AVNI member export.

The nightly sync of 28 Sep 2026 blanked MemberData.household_number. The export
(one row per member: City, Slum, household__first_name, member uuid) gives each
member's household. A number is written only where it is safe: the member is
stored once, the sheet's slum (or its SlumAlias) is the member's slum, that slum
has the household, and the member has no other number already.
`manage.py backfill_member_households <file>` prints the plan; `--apply` writes it.
"""

import csv
import re
from collections import Counter, defaultdict, namedtuple

from django.db import transaction
from django.db.models import Q

from graphs.models import HouseholdData, MemberData
from master.models import Slum
from survey.identity import household_number_from
from survey.locations import slum_id_for_name

COLUMNS = {
    "city": ("City", "address__City"),
    "slum": ("Slum", "address__Slum"),
    "number": ("household__first_name", "detailet_survey_House_Number"),
    "member": ("family_member - member_subject_id__uuid", "family_member_uuid"),
}
SKIP_CITIES = ("Test_city",)
BLANK = {"", "nan", "none", "null"}
FLOAT_SPELLING = re.compile(r"^(\d+)\.0+$")
MAX_LENGTH = MemberData._meta.get_field("household_number").max_length
BATCH = 2000

INCOMPLETE = "blank slum, number or member"
TWO_HOUSEHOLDS = "member listed in two households"
NOT_STORED = "member not in database"
STORED_TWICE = "member stored more than once"
NO_SLUM = "slum not found"
OTHER_SLUM = "household is in another slum"
NO_HOUSEHOLD = "no household with this number in the slum"
CONFLICT = "member already has another number"
TOO_LONG = "number too long"
SKIPPED_CITY = "skipped city"

REPORT_FIELDS = ("member_row_id", "member_uuid", "slum_id", "sheet_city", "sheet_slum", "sheet_number",
                 "old_number", "new_number", "action", "reason")

Change = namedtuple("Change", "row_id member_uuid slum_id city slum sheet_number old new action reason")
Plan = namedtuple("Plan", "changes skipped_cities")


def text(value):
    """Cell value as text; blank and the export's 'nan' become ''."""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    value = "" if value is None else str(value).strip()
    return "" if value.lower() in BLANK else value


def spelled(number):
    """A household number as the sync writes it: '0042' -> '42', '70.0' -> '70'."""
    number = text(number)
    match = FLOAT_SPELLING.match(number)
    return household_number_from(match.group(1) if match else number)


def read_rows(path):
    """Yield {city, slum, number, member} from an .xlsx or .csv export."""
    if path.lower().endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook

        book = load_workbook(path, read_only=True, data_only=True)
        try:
            for row in sheet_rows(book.worksheets[0].iter_rows(values_only=True)):
                yield row
        finally:
            book.close()
    else:
        with open(path, newline="", encoding="utf-8-sig") as handle:
            for row in sheet_rows(csv.reader(handle)):
                yield row


def sheet_rows(lines):
    header = [text(cell) for cell in next(lines)]
    found = {key: next((name for name in names if name in header), None) for key, names in COLUMNS.items()}
    missing = [" or ".join(COLUMNS[key]) for key, name in found.items() if name is None]
    if missing:
        raise ValueError("Missing column(s): {}".format(", ".join(missing)))
    index = {key: header.index(name) for key, name in found.items()}
    for line in lines:
        if not any(line):
            continue
        yield {key: text(line[position]) if position < len(line) else "" for key, position in index.items()}


def stored_members(uuids):
    """{member uuid: [(row id, slum id, household number)]} for the given uuids."""
    stored = defaultdict(list)
    uuids = sorted(uuids)
    for start in range(0, len(uuids), BATCH):
        rows = MemberData.objects.filter(member_uuid__in=uuids[start:start + BATCH])
        for row_id, uuid, slum_id, number in rows.values_list("id", "member_uuid", "slum_id", "household_number"):
            stored[uuid].append((row_id, slum_id, number))
    return stored


def households_in(slum_ids):
    """{(slum id, number as the sync spells it)} for the given slums."""
    rows = HouseholdData.objects.filter(slum_id__in=slum_ids).values_list("slum_id", "household_number")
    return {(slum_id, spelled(number)) for slum_id, number in rows}


def slum_resolver():
    """Slum id for a sheet slum name: SlumAlias title or Slum name, then a unique case-insensitive name."""
    cache = {}

    def resolve(name):
        if name not in cache:
            slum_id = slum_id_for_name(name, provider="avni")
            if slum_id is None:
                ids = list(Slum.objects.filter(name__iexact=name).values_list("id", flat=True)[:2])
                slum_id = ids[0] if len(ids) == 1 else None
            cache[name] = slum_id
        return cache[name]

    return resolve


def plan(rows, skip_cities=SKIP_CITIES):
    """Every member in the sheet with what would happen to her number."""
    skip = {city.lower() for city in skip_cities}
    by_member, changes, skipped_cities = defaultdict(list), [], 0
    for row in rows:
        if row["city"].lower() in skip:
            skipped_cities += 1
        elif not (row["slum"] and row["number"] and row["member"]):
            changes.append(Change("", row["member"], "", row["city"], row["slum"], row["number"], "", "",
                                  "skipped", INCOMPLETE))
        else:
            by_member[row["member"]].append(row)

    stored = stored_members(by_member)
    resolve = slum_resolver()
    households = households_in({slum_id for rows_ in stored.values() for _, slum_id, _ in rows_})

    for uuid, member_rows in sorted(by_member.items()):
        row = member_rows[0]
        new = spelled(row["number"])
        targets = stored.get(uuid, [])
        homes = {(resolve(item["slum"]), spelled(item["number"])) for item in member_rows}

        def change(action, reason="", target=("", "", None)):
            row_id, slum_id, old = target
            return Change(row_id, uuid, slum_id, row["city"], row["slum"], row["number"], old, new, action, reason)

        if len(homes) > 1:
            changes.extend(change("skipped", TWO_HOUSEHOLDS, target) for target in targets or [("", "", None)])
            continue
        if not targets:
            changes.append(change("skipped", NOT_STORED))
            continue
        if len(targets) > 1:
            changes.extend(change("skipped", STORED_TWICE, target) for target in targets)
            continue
        target = targets[0]
        slum_id, old = target[1], target[2]
        sheet_slum = resolve(row["slum"])
        old_spelled = spelled(old)
        if sheet_slum is None:
            changes.append(change("skipped", NO_SLUM, target))
        elif sheet_slum != slum_id:
            changes.append(change("skipped", OTHER_SLUM, target))
        elif len(new) > MAX_LENGTH:
            changes.append(change("skipped", TOO_LONG, target))
        elif (slum_id, new) not in households:
            changes.append(change("skipped", NO_HOUSEHOLD, target))
        elif old_spelled and old_spelled != new:
            changes.append(change("skipped", CONFLICT, target))
        elif old == new:
            changes.append(change("unchanged", "", target))
        else:
            changes.append(change("updated", "", target))
    return Plan(changes, skipped_cities)


def guarded_update(row_ids, old, new):
    """Write `new` only on rows still holding `old`, so a number set meanwhile is kept."""
    written = 0
    for start in range(0, len(row_ids), BATCH):
        rows = MemberData.objects.filter(id__in=row_ids[start:start + BATCH])
        if text(old):
            rows = rows.filter(household_number=old)
        else:
            rows = rows.filter(Q(household_number__isnull=True) | Q(household_number__regex=r"^\s*$"))
        written += rows.update(household_number=new)
    return written


def apply_changes(member_plan):
    """Write every planned update; returns the number of rows written."""
    groups = defaultdict(list)
    for item in member_plan.changes:
        if item.action == "updated":
            groups[(item.old, item.new)].append(item.row_id)
    with transaction.atomic():
        return sum(guarded_update(ids, old, new) for (old, new), ids in groups.items())


def write_report(path, member_plan, apply):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(REPORT_FIELDS)
        for item in member_plan.changes:
            action = item.action if apply or item.action != "updated" else "would update"
            writer.writerow([item.row_id, item.member_uuid, item.slum_id, item.city, item.slum, item.sheet_number,
                             item.old or "", item.new, action, item.reason])


def run(path, apply=False, report="member_household_backfill.csv", out=print, skip_cities=SKIP_CITIES):
    """Plan from the export, write the report, and with `apply` write the numbers. Returns counts."""
    member_plan = plan(read_rows(path), skip_cities)
    counts = Counter()
    by_city = Counter()
    for item in member_plan.changes:
        counts[item.action] += 1
        if item.reason:
            counts[item.reason] += 1
        if item.action == "updated":
            by_city[item.city or "(blank city)"] += 1
    counts[SKIPPED_CITY] = member_plan.skipped_cities
    write_report(report, member_plan, apply)
    if apply:
        counts["written"] = apply_changes(member_plan)

    out("{} members to update, {} already right, {} skipped, {} rows of skipped cities.".format(
        counts["updated"], counts["unchanged"], counts["skipped"], counts[SKIPPED_CITY]))
    for reason in (INCOMPLETE, TWO_HOUSEHOLDS, NOT_STORED, STORED_TWICE, NO_SLUM, OTHER_SLUM, NO_HOUSEHOLD,
                   CONFLICT, TOO_LONG):
        if counts[reason]:
            out("  skipped, {}: {}".format(reason, counts[reason]))
    for city, count in sorted(by_city.items()):
        out("  to update in {}: {}".format(city, count))
    out("Report: {}".format(report))
    if apply:
        out("Written: {} members. Refresh the member summary next (job member_summary).".format(counts["written"]))
    else:
        out("Dry run: nothing written. Run again with --apply to write.")
    return counts


def restore(report, apply=False, out=print):
    """Undo an applied run from its report: put each old number back where the new one is still in place."""
    groups = defaultdict(list)
    with open(report, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["action"] == "updated":
                groups[(row["old_number"], row["new_number"])].append(int(row["member_row_id"]))
    restored = 0
    with transaction.atomic():
        for (old, new), ids in groups.items():
            for start in range(0, len(ids), BATCH):
                rows = MemberData.objects.filter(id__in=ids[start:start + BATCH], household_number=new)
                restored += rows.update(household_number=old or None) if apply else rows.count()
    out("{} {} members.".format("Restored" if apply else "Would restore", restored))
    return restored
