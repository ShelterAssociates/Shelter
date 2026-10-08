# Slum data versions — what was built, and how to run it

Everything added for re-surveying a slum that was registered under a second AVNI
location. Written while working on Antule Nagar (slums 1923 and 2021), but the
feature is general: it works for any slum.

Nothing in here is specific to one slum except §6, which is the Antule Nagar
runbook.

---

## 1. The problem

Antule Nagar existed twice:

| Slum | Name | Had |
|---|---|---|
| 1923 | Antule Nagar, Pisoli | RIM + factsheet, 343 households, 560 components |
| 2021 | Antule Nagar, Pisoli New | no RIM row, 353 households, 508 components |

The factsheet button never appeared for 2021, because
`master.views.rim_factsheet_available` requires both a `Rapid_Slum_Appraisal`
row and a `graphs.SlumData` row, and 2021 had no `SlumData`.

Underneath that sat four structural limits:

1. `survey.SlumAlias` allowed **one AVNI location per slum**, so the new
   location could not feed the old slum.
2. The legacy tables the public map reads carry **no version column**, so a
   re-survey would overwrite the previous one in place.
3. RIM and the factsheet were not version-aware at all.
4. Mapped components (the KML layers) point at a slum **generically**, so they
   were invisible to anything that walked the slum's relations.

---

## 2. What the feature does

**Starting a new version** on a slum copies every registered table into
`survey.SlumVersionBackup` and **leaves the live tables alone**. The public map,
graphs and exports keep showing the old survey. The first record modified after
the version started switches the live household tables over: the old rows are
deleted there and survive in the backup and in the `survey.Record` mirror. From
then on, a record older than the version's start is kept out of the live tables
whatever order AVNI sends records in.

**RIM is never switched automatically.** It is an explicit choice when the
version starts — keep / clear / re-sync from a chosen location — and can be
changed later. Whatever is chosen the old RIM is archived, so the factsheet
gains a **version picker**: the public page shows the current survey and the
older ones stay readable.

**Components are archived but never cleared.** Re-uploading a KML replaces one
layer at a time, so the team removes and re-draws layers by hand. The archive
copy is the only record of what the previous survey mapped.

**A slum can take data from several AVNI locations**, one of them the primary
(the RIM source). Records are matched on the location title, so a re-survey
registered under a new location reaches the original slum.

**Per slum, sync can be switched off** (records are skipped and the slum is
named in the nightly digest) and **its locations locked** against the nightly
AVNI location refresh. Editing locations on the page locks them automatically.

---

## 3. Models (`survey/models.py`)

| Model | Change |
|---|---|
| `SlumAlias` | New `is_primary` (default `True`). Dropped `unique_together (slum, provider)`; added conditional constraint `survey_alias_one_primary` unique `(slum, provider)` **where `is_primary`**. So several locations per slum, exactly one primary. `(provider, external_id)` still unique. |
| `SlumDataVersion` | New `switched_on` (nullable; empty = the live tables still serve the previous version) and property `is_waiting`. |
| `SlumVersionBackup` | **New.** One frozen row of an older version: `slum`, `version`, `source_model` (`"graphs.HouseholdData"`), `source_pk`, `data` (`jsonfield.JSONField`, Django's own serialised shape), `archived_on`. Indexed on `(slum, version)` and `(slum, version, source_model)`. Read-only in the admin. |
| `SlumSyncSetting` | **New.** Per-slum control; **no row means today's behaviour**: `sync_enabled` (default `True`), `alias_locked` (default `False`), `note`, `updated_by`, `updated_on`. |

Migration: `survey/migrations/0003_slum_versions_and_sync_settings.py`, written by
hand to match the models (migrations are gitignored in this project). Its
`RunPython` step marks existing aliases primary and treats existing versions as
already switched on, so nothing already versioned changes behaviour.

### PostgreSQL 9.3 on production

Production runs **PostgreSQL 9.3.24** with Django 3.0.7; development runs
PostgreSQL 16 with Django 3.2. Django 3.0 officially needs PostgreSQL 9.5+, and
its PostgreSQL introspection query uses `unnest(...) WITH ORDINALITY`, which
arrived in **9.4**. So anything that makes Django introspect the schema fails on
production with:

```
psycopg2.errors.SyntaxError: syntax error at or near "WITH ORDINALITY"
```

`AlterUniqueTogether` is exactly that: a `unique_together`'s constraint name is
generated, so Django introspects the table to find it before dropping it. A
**named** `UniqueConstraint` is dropped by its name and needs no introspection.

Two things follow, and both are done:

1. **`SlumAlias` declares no `unique_together`.** Both uniqueness rules are
   named constraints, so any future change to them is 9.3-safe.
2. **The one-time removal of the old pairs** is wrapped in
   `migrations.SeparateDatabaseAndState`: Django gets the state change, and the
   database gets SQL from the migration's own `drop_unique_on(table, columns,
   except_name)` helper, which finds a unique constraint **by its columns** and
   drops it by name. Everything it uses (`DO` blocks, `format('%I')`,
   `array_agg(... ORDER BY ...)`) predates 9.3. `except_name` exempts the
   replacement constraint, which covers the same columns, so a re-run is a
   genuine no-op.

Verified on a throwaway database shaped like production: the old generated
constraints go, the named one and the partial unique index arrive, a second
location on one slum is allowed, a second primary and a duplicate uuid are both
refused, and re-running the drops leaves the new constraint standing.

`SlumDataVersion` and `SyncSwitch` still use `unique_together`. They are
untouched by this work so no migration is generated for them, but if either ever
changes, it will need the same treatment.

---

## 4. Code

### `survey/versioning.py` (new)

The registry and the version machinery.

- `Table(label, app, model, slum_field, generic=False)`. `generic` means the
  model points at the slum through a content type and an object id, which is how
  `component.Component` does it.
- `HOUSEHOLD_TABLES` — `graphs.HouseholdData`, `FollowupData`, `MemberData`,
  `MemberProgramData`, `MemberEncounterData`, `mastersheet.ToiletConstruction`,
  `CommunityMobilization`, `CommunityMobilizationActivityAttendance`.
- `RIM_TABLES` — `graphs.SlumData`, `master.Rapid_Slum_Appraisal`.
- `COMPONENT_TABLES` — `component.Component` (generic), `component.ComponentMetric`.
- Derived tables (dashboard aggregates, QOL, splits) are deliberately out: the
  dashboard refresh rebuilds them.

| Function | What it does |
|---|---|
| `start_new_version(slum_id, user, rim_choice, rim_location, note)` | Archives every registered table as version N, creates version N+1 with `switched_on=None`, applies the RIM choice. Live tables untouched. |
| `allows_write(slum_id, moment)` | Called per record by the household writer. Unversioned slum → always writes. Version waiting → writes, and the first record at/after `started_on` calls `go_live`. Version live → a record older than `started_on` is refused. |
| `go_live(slum_id)` | `ensure_backup` first, then deletes `HOUSEHOLD_TABLES` rows and stamps `switched_on`. RIM and components are never cleared. |
| `missing_backup_tables` / `ensure_backup` | Archive, **per table**, whatever a version has not archived — covers a version added through the admin, and a version started before a table joined the registry. |
| `set_rim_source(slum_id, external_id)` | Moves the primary alias. |
| `backup_fields`, `values_shaped`, `rim_at`, `rim_backup_versions`, `rim_choices_for` | Read a frozen version back. `backup_fields` parses JSON-string values (jsonfield dumps a JSONField as a string). `values_shaped` renames FK keys to `<name>_id` to match `QuerySet.values()`. |
| `describe(slum_id)` | What the page shows. |

No module-level cache: the web process would otherwise hold a stale answer after
the page changed something.

### `survey/slum_sync.py` (new)

`is_enabled`, `is_alias_locked`, `disabled_slum_ids`, `locked_slum_ids`,
`refuses(slum_id, slum_name)` (true when sync is off, reporting the skip),
`report_skipped` (counts the skip and names the slum for the digest),
`update(...)` (leaves unnamed flags alone).

### `survey/merging.py` (new)

Merge one slum into another, then delete it. Walks **every reverse relation** on
`master.Slum` **and every `GenericRelation`** — without the second walk
`component.Component` is invisible and a merge would leave a slum's whole KML as
orphaned geometry pointing at a deleted id.

`plan_merge` returns `{moving, blocked, unreadable, records, aliases}`.
`blocked` = rows whose `unique_together`-with-slum key the target already holds.
`unreadable` = tables whose columns do not match their model. `merge` refuses
while anything is blocked or unreadable (checks run **before** the transaction
opens, since a failed query would abort it), writes a JSON dump, re-points rows,
stamps moved `Record`s, moves aliases over as secondary, deletes the source.

### `survey/locations.py`

- `slum_and_city_ids(name)` — an **alias title now wins over `Slum.name`**, still
  raising `LookupError` when nothing matches.
- New `slum_id_for_title`, `slum_id_for_name` (None instead of raising),
  `slum_external_ids` (all locations, primary first).
- `slum_external_id` → the **primary** only. `slum_ids_for` → distinct.

### `survey/connector.py`

Two gates on the record's resolved slum, before storing:

- `only_slums` (a location-filtered run) → counts `out_of_scope`, skips.
- `slum_sync.refuses` → counts `sync_off`, skips, names the slum in the digest.

`sync_kind(..., locations=None)` turns provider location ids into allowed slum
ids and also hands them to `provider.iter_records` so a subject listing is
narrowed server-side.

### `survey/views.py`, `urls.py`, templates (new)

The superuser page, §5.

### avni app

| File | Change |
|---|---|
| `locations.py` | `slum_location_uuids` (all), `slum_id_for_location_title`; `slum_location_uuid` stays primary-only. |
| `media.py` | The photo fallback scan iterates **every** mapped location, primary first — otherwise households under a second location are never found. |
| `provider.py` | `iter_records(..., locations=())` narrows the AVNI request for subject listings (`list_path` takes `location_uuid`); other kinds are filtered by slum after the fetch. Page walking split out into `iter_path`. |
| `sync/households.py` | `allows_write` gate before writing; `merge_into_rhs_data` resolves the slum id instead of joining on `slum_id__name`; `sync_households(..., locations=None)`. |
| `sync/rim.py` | Both slum-level syncs respect `slum_sync.is_enabled`. `save_toilet_record(record, slum_id=None)` takes the slum being synced, so a toilet never lands anywhere else. |
| `sync/encounters.py`, `file_imports.py`, `members.py` | Name lookups go through the shared `slum_id_for_name`, so alias titles work everywhere. |
| `sync/locations.py` | The nightly match builds its alias map from **primary** rows, treats known secondary uuids as already matched, and **skips locked slums** (reported as `locked`). |
| `jobs/manual_sync.py` | `wanted_locations(params)`; `rhs_sync` and `household_encounter_sync` take `locations`. |
| `management/commands/load_slum_locations.py` | **Keyed on the uuid, never the slum.** Never re-points an existing alias, reports a uuid held by another slum, skips locked slums. Prints `N created, N already mapped, N locked, N unknown`. |

### avni_console

`location_choices()` and a **Locations** multi-select on `rhs_sync` and
`household_encounter_sync` (nothing picked = every location = previous
behaviour), plus the `locations` param builder.

### notification

- `reporting.note_slum(key, slum)` — adds a slum name to a comma-separated list
  on the active step.
- `email.digest_payload` / `digest_run` — the digest as structured data.
- `nightly_digest_email.html` **restyled**: status-coloured card, per-run
  headers, facts table, per-step counts, city tables, cause lines, and a
  highlighted line naming any slum whose sync is off. The plain-text part is
  unchanged, so existing readers and tests are unaffected.

### reports / master (factsheet versions)

- `master.views.rim_factsheet_available` now returns `{available, versions}`.
  Available when live RIM exists **or** an older RIM is archived, so clearing
  RIM does not make the button vanish.
- `reports/services/rim_factsheet.py`: `get_rim_factsheet_detail(slum_code, version)`
  and `rim_factsheet_view(slum_id, raw, version)` read a frozen RIM from the
  backup. `with_version` re-attaches the version keys after `map_rim_data`
  rebuilds the context.
- `reports/views.py`: `wanted_version(request)` (`?version=N`),
  `rim_cache_key`, and `rim_report_id` → `<slum>-vN`, so two viewers on
  different surveys cannot collide in the PDF service.
- `static/js/master_map_boundaries.js`: a `<select id="factsheetVersion">`
  appears only when a slum has more than one survey, and its choice is appended
  to the preview, generation and download calls.

### Two bugs the real data caught

- The backup stores `rim_data` as a **JSON string**, so it needed parsing.
- The appraisal's foreign key is stored under `slum_name`, which shadowed the
  slum's display name — version 1 rendered its name as "1923". `values_shaped`
  fixes it.

---

## 5. The page — `/slum-versions/`

**Superusers only** (`superuser_required`; everyone else gets 403). Linked in
Admin → Tools directly under Upload KML, shown only to superusers.
Internal-only: nothing here is public.

| Method | Path | Purpose |
|---|---|---|
| GET | `/slum-versions/` | Slum **search** — client-side filter over a server-rendered index, arrow keys / Enter / Escape, tags for version, waiting and location count — plus a "Recently versioned" card |
| GET | `/slum-versions/<id>/` | Live row counts per table, version history with per-version backup counts and status, mapped locations, sync settings; warns when a version is missing a backup |
| POST | `.../settings/` | `sync_enabled`, `alias_locked`, `note` |
| POST | `.../locations/add/` | Map a location (uuid + title); first becomes primary, later ones secondary; a uuid mapped elsewhere is refused |
| POST | `.../locations/remove/` | Unmap |
| POST | `.../locations/primary/` | Make one location the RIM source |
| POST | `.../version/start/` | Start the next version; needs `rim_choice` and the typed word `START` |
| POST | `.../version/backfill/` | Archive anything the waiting version has not backed up; refused once the version is live |
| POST | `.../merge/` | `dry_run=1` reports; otherwise needs the typed word `MERGE`, writes a JSON dump, moves data and **deletes** the other slum |

Editing locations here **auto-locks** the slum.

Files: `survey/templates/survey/slum_versions.html`,
`survey/templates/survey/partials/styles.html`,
`static/js/slum_version_search.js`.

---

## 6. Antule Nagar runbook

State as of the last dry run: 1923 is at **version 2, waiting**; version 1 is
fully backed up (343 households, 245 follow-ups, 839 members, 1 RIM, 1
appraisal, 560 components); both locations are mapped to 1923 with the old one
primary; statuses flipped (1923 active, 2021 inactive).

### Already done

1. Mapped 2021's AVNI location onto 1923 as a secondary location.
2. Started version 2 with RIM choice **keep**.
3. Backed up what was missing (the 560 components).
4. Flipped `status`: 1923 active, 2021 inactive.

### The move — commands

Dry run first. It changes nothing and prints exactly what would happen.

```bash
cd /srv/Shelter            # wherever manage.py lives on the server
source <your venv>/bin/activate

python manage.py adopt_slum_data --from 2021 --into 1923
```

Expected output:

```
would clear from the target (already archived):
   Households                             343
   Follow-ups                             245
   Family members                         839

would move from the source:
   mastersheet.communitymobilization      4
   graphs.householddata                   353
   graphs.followupdata                    242
   graphs.memberdata                      712
   helpers.slumphotoupload                1
   survey.record                          0

components, mode per-layer:
   target would end with 601 (93 kept + 508 brought)

RIM is not moved: the target keeps its own factsheet data.
```

If those numbers look right, run it for real with a dump:

```bash
python manage.py adopt_slum_data --from 2021 --into 1923 \
  --apply --dump /srv/Shelter/antule_nagar_move_$(date +%Y%m%d%H%M).json
```

What `--apply` does, in one transaction:

1. Archives anything the outgoing version has not archived (nothing is ever
   deleted while it exists nowhere else).
2. Clears 1923's household tables and stamps the version live.
3. Moves 2021's households, follow-ups, members, mobilization and photo upload
   onto 1923.
4. Components **per layer**: drops 1923's copy of each of the 15 layers 2021
   also has, brings 2021's 508 across. The 9 layers only 1923 has (Chambers 50,
   Kutcha road 17, Closed gutter 8, Manholes 3, Open defecation areas 3,
   Compound wall 2, Slum boundary 1, Hand Pumps 1, "Location of the  Supply
   pole" 8 = 93) are untouched. 1923 ends with **601**.
5. Leaves RIM on both slums and leaves the Slum 2021 row in place, empty and
   inactive.

### After it

```bash
# what 1923 holds now
python manage.py shell -c "
from survey import versioning
for t in versioning.ALL_TABLES:
    n = versioning.rows_for(t, 1923).count()
    if n: print(t.label, n)
"
```

Then check in the browser: 1923 on the public map, its factsheet button, and the
factsheet version picker (Current / Version 1).

### Flags

| Flag | Use |
|---|---|
| `--components missing-only` | Only bring layers 1923 lacks; overlapping layers keep 1923's older drawing |
| `--components all` | Replace every component with 2021's (the 9 1923-only layers would leave the live map) |
| `--skip-household-clear` | Leave 1923's household rows (they would then collide) |
| `--dump PATH` | JSON copy of every row that moves — always use it on production |

### Rollback

There is no undo button. What you have: the `--dump` file, the version 1 backup
in `survey_slum_version_backup`, and the `survey.Record` mirror at version 1.
Restoring from the backup is a manual job today — say the word if you want a
restore command.

---

## 7. What is deliberately not done

- **RIM is not moved** by `adopt_slum_data`. 2021's appraisal has 15 filled
  fields against 1923's 32 and no `SlumData` at all, and a second appraisal row
  on one slum makes the factsheet ambiguous. 1923 keeps its own.
- **Slum 2021 is not deleted.** Its data moves out and the row stays, inactive
  and empty. Deleting it later is a separate, confirmed step.
- **Restoring from the backup** has no command yet.
- **Metabase views** (`DBScripts/vw_survey_*.sql`) still expose `version`
  without filtering it. Unchanged.

---

## 8. Tests

**802 tests, 800 pass.** The 2 failures are
`master.tests.RimDisplayFilterTests`, which **fail on a clean tree too** —
pre-existing and unrelated.

| File | Covers |
|---|---|
| `survey/tests/test_versioning.py` | Starting a version (backup counts, live tables untouched, stacking, other slums unaffected), going live (household tables only, RIM kept, idempotent, a version made in the admin backed up first, record ordering), the three RIM choices, per-slum sync settings |
| `survey/tests/test_slum_scope.py` | The sync-off gate and its digest line, the location filter end to end, several locations per slum, title routing, the merge (dry run, apply, version stamping, blocked keys, unreadable tables, self-merge), the superuser page and its actions |
| `survey/tests/test_rim_versions.py` | RIM backup accessors (live vs frozen, JSON-string decode, unknown versions), the availability API's version list, the factsheet reading a chosen version, the versioned PDF report id, auto-lock, the slum search index |
| `survey/tests/test_component_versions.py` | Components found generically, archived, never cleared at go-live, surviving a layer replacement, one set per version; the per-table backfill and its refusal after go-live; the merge moving components instead of orphaning them |
| `survey/tests/test_adopt_slum_data.py` | Dry run changes nothing; apply clears then moves; cleared rows recoverable; RIM left on both; the three component modes; metrics follow their layer; unbacked rows archived first; refusal with no waiting version; the dump |
| `avni/tests/test_version_sync.py` | A real household sync against a versioned slum: first new record switches over, old records stay out, a repeated household number, a second location title feeding the same slum |
| Updated | `survey/tests/test_slum_alias.py` (the loader's new contract), `avni/tests/test_locations_match.py` (locked slums, second locations), `avni/tests/test_rim.py` (sync-off, primary-only, toilet slum), `notification/tests.py` (the styled digest), `survey/tests/fakes.py` + `survey/contracts.py` (`iter_records(..., locations=())`) |

### Running them here

The project's own test database cannot be built normally: `master/migrations`
0004, 0007 and 0023 set `PolygonField(default='')`, which modern GDAL rejects,
and `run_syncdb` then trips over a duplicate auth permission. Neither is related
to this work, so the suite was run with a settings module and test runner kept
**outside the repo** that build the schema from the models and create
permissions one at a time. That is a local workaround, not a project change.

---

## 9. Still open

| Item | Note |
|---|---|
| `reports.SponsorProjectMonthlyWorkProgress.location` | The model declares the FK but the column does not exist, so creating or saving a donor monthly report crashes (`initialize_monthly_work_progress`, the signal, and the admin inline). `adopt_slum_data` reports it and safely leaves it alone — with no column, no row can point at a slum. Fix with `makemigrations reports && migrate`. |
| Deleting slum 2021 | Not done; decide once 1923 looks right |
| `ActivityType.key` is `varchar(2)` | `avni/tests/test_mobilization.py` sets it to `str(activity.id)`, so the test breaks on a reused test database once ids pass 99. Pre-existing fragility |
| Fresh database builds | Blocked by the `PolygonField(default='')` migrations above |
| Restore-from-backup command | Not written |
