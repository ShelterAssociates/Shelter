# RIM version comparison — what changed, and why

Everything in this round of work: comparing two RIM surveys of the same slum on
the reports page, the public map losing its version picker, a shared slum
search box, two data-safety fixes in the versioning module, and one production
bug found along the way.

Written against the working tree as of 2026-10-09. Nothing here is committed.

---

## 1. What this adds

A slum that has been re-surveyed holds more than one RIM. Before this, only the
current one was reachable from the map's factsheet button, and there was no way
to see what the new survey changed.

Now:

- The **public map** shows the latest factsheet and nothing else. No version
  picker, one button.
- The **reports page** (`/reports/`) picks any survey, and shows a second pane
  with the two surveys side by side — every question, with the answers and
  pictures that moved highlighted.
- Both the factsheet and the comparison download as PDFs.

---

## 2. Public map — the version picker is gone

| File | Change |
|---|---|
| `static/js/master_map_boundaries.js` | `_showFactsheetBtn` renders one `.action-btn`. Removed: the collapsible toggle, its caret and body wrapper, the `_factsheetExpanded` global, the two version-picker helpers, and `?version=` on the preview, generation and OTP-download fetches. |
| `master/templates/city_wise_map.html` | `.factsheet-version` CSS removed. `.collapsible-toggle` kept — `ward_breakdown.js` and the GIS export panel still use it. |
| `master/views.py` | `rim_factsheet_available` returns `{available}` only, and is live-RIM-only again. |

### Behaviour change to be aware of

A slum whose RIM was cleared by a re-survey (RIM choice `clear` or `resync`)
now shows **no factsheet button on the public map** until new RIM arrives. It
previously fell back to the newest archived version.

This was deliberate — "the map always offers the latest and nothing else" — and
`survey/tests/test_rim_versions.py` was updated to match. The test that
asserted the opposite (`test_a_cleared_rim_keeps_the_factsheet_available_from_the_backup`)
is now `test_a_cleared_rim_removes_the_factsheet_from_the_map`. The archived
factsheet is still reachable from the reports page.

Reverting is one line in `rim_factsheet_available`.

---

## 3. The comparison itself

### `reports/services/rim_compare.py` (new, 149 lines)

Pure: no database, no network. It compares two contexts that
`rim_factsheet.map_rim_data` has already built.

```python
compare(old, new, old_raw=None, new_raw=None)
```

Returns, or `None` when nothing moved:

```python
{
  "sections": {
     "General": {
        "fields": {"Year Established": {"old": "1970", "new": "1975", "changed": True}, ...},
        "images": {"map":    {"old": <url>, "new": <url>, "changed": False},
                   "photo1": {...}, "photo2": {...}},
        "meta":   {...},        # the newer side's map/photo flags
        "changed": 10,          # how many moved in this section
     },
     ...
  },
  "count": 64,                  # how many moved in total
}
```

Points worth knowing:

- **Every section and every question is kept**, not only what changed. The PDF
  reads like the factsheet, so unchanged answers are listed too, marked
  `changed: False`. The result is `None` only when nothing at all moved, which
  is how the page knows not to offer a Changes tab.
- **Values are already strings.** `map_rim_data` runs everything through
  `_to_str`, so this is plain string comparison with no type guessing.
- **A picture is compared on its stored appraisal column, never on the URL
  shown.** AVNI signs a fresh URL on every fetch, so comparing displayed URLs
  would report every picture as replaced, every time. `old_raw` / `new_raw` are
  the two `Rapid_Slum_Appraisal` rows as stored, fetched by
  `reports.views.rim_raw` via `versioning.rim_at`. Without them, no picture is
  claimed to have changed — the function does not guess.
- A field only the newer survey has reads as `NA → value`, which is a real
  change: a re-survey often collects a topic the previous one skipped.

### `reports/views.py`

New:

| Function | Purpose |
|---|---|
| `rim_versions` | JSON list of the surveys on offer |
| `rim_comparison` | HTML fragment of the two surveys; **empty body when nothing changed** |
| `rim_comparison_pdf_generation` | the same through the PDF microservice |
| `previous_version(slum_id, version)` | the archived version just before one |
| `wanted_baseline(request, slum_id, version)` | the `?against=` side, falling back to `previous_version` |
| `comparison_for(slum_id, version, baseline)` | builds both contexts and compares |
| `rim_context(slum_id, version)` | the briefly-cached factsheet context, now shared by every RIM view |
| `rim_raw(slum_id, version)` | the appraisal row as stored |
| `version_tag(version)` | `current` or `v2`, for report ids |

`report_view` also hands the page `slum_search_index`, reusing
`component.views.build_slum_search_index` (already limited to the user's
permitted cities).

Both comparison views take `?version=` (the survey being read) and `?against=`
(the one it is read against). `against=current` is a real choice — an older
survey can be read against the live one — so an absent parameter and the live
survey are deliberately not the same thing.

### Routes (`reports/urls.py`)

```
/reports/api/rim_versions/<slum_id>/
/reports/rim-comparison/<slum_id>/
/reports/api/rim_comparison_generation/<slum_id>/
```

All three `@staff_member_required`.

### The PDF

`rim_comparison_pdf_generation` keeps `report_type: "rim_factsheet"`. The PDF
microservice only knows `rim_factsheet` and `donor_report`, so inventing a
third type would need a change outside this repo. The stored file is kept
apart by report id instead: `<slum>-v3-vs-v2`, built by `rim_report_id`.

Download reuses `rim_factsheet_pdf_fetch` with `compare=1`, so the OTP/staff
gate is shared rather than duplicated.

### Templates

| File | |
|---|---|
| `reports/templates/reports/rim_factsheet/compare.html` | screen fragment |
| `.../pdf/compare_pdf.html` | the PDF |
| `.../partials/compare_body.html` | the content, shared by both |
| `.../partials/compare_styles.html` | the styles, shared by both |

Two things to know before editing these:

1. **Every shared rule is scoped to `.compare-root`.** The fragment's `<style>`
   is injected straight into the reports page, so a bare `body` or `*` rule
   restyles the whole page. An earlier version of this did exactly that — it
   set `body { background: #e6e6e6 }` and a global box-sizing reset on the
   report tool every time you pressed Generate. The PDF template declares the
   page-level rules itself.
2. **Use `{% comment %}`, not `{# #}`, for anything spanning more than one
   line.** `{# #}` is single-line only in Django, so a multi-line one renders
   its tail into the page as visible text.

PDF layout:

- **A3 portrait, 29.7 × 42cm** — not the factsheet's 14 × 15cm. This page
  carries four text columns plus a before/after picture pair per slot, so it
  needs the width and the height.
- The change count rides in the **fixed header**, repeated on every page,
  rather than taking a page of its own.
- One section per page (`page-break-after: always`).
- A section with more than nine questions gets `compare-section--dense` from
  the template and is set a step tighter, which is what keeps the long ones
  (Toilet 13, General 12) on one page. Short sections stay full size.
- If a section still runs long it breaks between rows, not through one, and
  `thead` repeats the column headings.

`compare_body.html` takes `hide_summary`, so the same partial serves the screen
(summary above the panel) and the PDF (summary in the header).

---

## 4. Reports page UI

- **Slum search** above the dropdowns; picking one fills City → Administrative
  Ward → Electoral Ward → Slum. The dropdowns stay hidden until a slum is
  picked, with an "or choose with the dropdowns" link for browsing.
- **Survey Version** picks the factsheet shown; **Compare** picks the two sides
  of the comparison, left and right. Both appear only when the slum has more
  than one survey.
- The preview pane has a **segmented toggle in its own header** — `Factsheet` /
  `Changes (64)`. One pane at a time. The Changes tab only exists when there is
  a difference.
- `Download Changes PDF` follows the same flow as the factsheet PDF: generated
  as soon as a difference is found, greyed and labelled *Preparing…* until the
  service has it, then enabled.
- Both cards are the same box — `align-items: stretch`, a shared height, and
  only the pane body scrolls so the tab bar stays put.

The page's three near-identical cascade `$.post` blocks were factored into one
promise-returning `loadInto()`, shared by the change handlers and the search.

---

## 5. Shared slum search — `static/js/slum_search.js` (new)

The KML upload page and the reports page now use one component.

```js
SlumSearch.readIndex(nodeId)                  // the json_script index, lower-cased once
SlumSearch.create({index, $input, $results, prefix, limit, onPick})
SlumSearch.enableListKeyboard({...})          // arrow keys for any list of rows
```

They differ only in class prefix and what a pick does — the KML page opens its
confirm modal, the reports page fills the dropdowns. `enableListKeyboard` was
already generic inside `component_list_kml_upload.js`; it was lifted, not
rewritten, and that file shed 196 lines. Its "recent uploads" list uses the
shared helper too.

**Every row is built with `.text()`, never `.html()`.** Slum and ward names are
user-entered database values. The reports page's first implementation
interpolated them into an HTML string, which was an injection hole on
staff-entered data; the shared component closes it.

---

## 6. Versioning — two data-safety fixes

Both are in the existing deferred-switch model: starting a version archives the
slum's rows and **leaves the live tables alone**, and the first record of the
new survey triggers `go_live`, which deletes them.

### 6.1 Rows arriving after the checkpoint were deleted unarchived

`missing_backup_tables` checks per **table**, not per row. `HouseholdData`
already had backup rows from the checkpoint, so it counted as archived — and
`go_live` then deleted every household including the ones that had arrived
since, which existed nowhere else.

`go_live` now calls `refresh_household_backup(slum_id, version)`, which
re-archives the live household rows as the outgoing version immediately before
deleting them, so the snapshot matches exactly what goes. It touches only
`HOUSEHOLD_TABLES` — RIM and components keep their checkpoint copy — and skips
a table with no live rows, so an earlier snapshot is never replaced with
nothing.

Covered by `test_versioning.LateOldVersionRowsTests`.

### 6.2 A version added through the admin archived nothing

`SlumDataVersionAdmin` allows adding a version row directly, which bypasses
`start_new_version` entirely — a checkpoint with no snapshot, and therefore a
version with no comparison. `save_model` now calls `versioning.ensure_backup`
on create and reports what it froze.

Covered by `test_rim_versions.EveryCheckpointArchivesRimTests`, which also pins
the existing guarantee that **RIM is archived at every checkpoint whatever the
RIM choice** — keep, clear or resync. That was already true; it now has tests.

---

## 7. Production bug found: every AVNI map read as missing

`reports.services.rim_factsheet.is_image_reachable` used `requests.head`.

**AVNI presigns its media for GET only.** A presigned URL's signature is
method-specific, so S3 answers a HEAD with `403`:

```
HEAD <signed url>  →  403  application/xml
GET  <signed url>  →  206  image/jpeg
```

`map_rim_data` calls that function for every section's map and sets the value
to `"NA"` when it returns False — so the factsheet has been printing
`MAP NOT AVAILABLE` for slums whose map is perfectly fine, wherever the map is
AVNI-hosted.

It now does a ranged `GET` with `Range: bytes=0-512`, accepting `200` or `206`,
and closes the response without reading the body. Two tests pin it: a URL that
refuses HEAD but serves GET is reachable, and a 404 is not.

**This changes production output** — maps that showed as unavailable will start
rendering.

---

## 8. Local demo data — `survey/management/commands/make_local_test_slum.py`

Development only. It refuses to run unless the database host is local **and**
`DEBUG` is on — two independent checks, because it writes rows and deletes
them.

```
python manage.py make_local_test_slum            # build it
python manage.py make_local_test_slum --remove   # delete it
```

Builds `ZZ LOCAL TEST SLUM (delete me)` with its own city/ward chain and three
RIM surveys, so the version picker and the comparison have something to show.

How the data is made believable:

- A real slum's RIM is copied as survey 1.
- For each later survey, **~70% of the answers the factsheet actually prints**
  are changed. The targets come from `RIM_FIELD_DISPLAY_NAMES` — mutating raw
  keys at random barely moves the comparison, because most keys never reach the
  factsheet. An early version changed 9 answers and only 3 showed up.
- **~60% of the questions the source left blank are answered**, which is the
  only way a section the source never filled in (Electricity, here) shows
  anything.
- Pictures are borrowed from the **newest** appraisal rows, and **each one is
  fetched first to confirm it loads**. Most older rows point at `ShelterPhotos`
  files long gone from the media server, so borrowing blindly filled the demo
  with 404s.

Typical result: ~64 changes between consecutive surveys, picture changes in
every section, and every picture URL resolving.

`--remove` deletes row by row rather than calling `slum.delete()`. Django's
cascade walks every relation pointing at `Slum`, and that scan fails on a local
database with migrations outstanding
(`reports_sponsorprojectmonthlyworkprogress.location_id does not exist`).

---

## 9. Unrelated changes in the same working tree

| File | |
|---|---|
| `graphs/admin.py` | `APICache` registered: read-only, newest first, exact-match search on `request_hash`. The changelist defers `response`, or the jsonfield would deserialise every cached payload just to render a list that does not show them. |
| `master/tests.py` | Five stale mock assertions. `rimdisplay` and `filterMasterList` moved to multi-select `__in` lookups; the tests still expected the single-value form. **No production code touched.** |

---

## 10. Testing

```
python manage.py test survey avni avni_console notification component reports master graphs \
    --settings=shelter.test_settings --noinput
```

808 tests, all passing. `reports/tests.py` grew by 335 lines.

The pure logic was written test-first: `compare()`, `previous_version`, the
image-comparison rules, `is_image_reachable`, and both versioning fixes each
had a failing test before the code existed. The comparison *views* were written
before their tests.

### Not verified

- **The rendered PDF.** Page rules, page size, image tags and highlight classes
  are confirmed in the generated HTML, but whether every section truly lands on
  one page depends on the PDF engine. The levers are the dense threshold
  (currently nine questions) and the picture `max-height`.
- **The PDF microservice round trip.** `rim_comparison_generation` POSTs to
  `PDF_SERVICE_URL`; nothing here has exercised a real response.
- **Both pages in a browser.** Syntax, template rendering and the test suite
  pass; no page was loaded by an automated check.
- One donor image in the demo is `image/heic`, which passes the reachability
  check but may not render in a browser or the PDF engine.

---

## 11. Still open

`avni/sync/households.py` builds its `Household` namedtuple with

```python
submitted_on=(record.get("audit") or {}).get("Last modified at")
```

so the field named `submitted_on` actually carries **last-modified**. That
value is what `versioning.allows_write` compares against `started_on` to decide
the version switch. An edit to an *old* household in AVNI therefore has a
last-modified after the checkpoint, counts as the new survey's first record,
and triggers `go_live` — deleting every live household row for that slum. The
data survives in `SlumVersionBackup`, but the slum goes blank on the public map
until the real re-survey arrives.

The fix is to trigger on registration time instead — `record["audit"]["Created at"]`,
which `avni/sync/rim.py` already reads. It is not done here because it changes
*when* the switch fires, and one case needs checking first: if a re-survey
edits existing AVNI subjects rather than registering new ones, their
`Created at` is old and the switch would never fire at all.
