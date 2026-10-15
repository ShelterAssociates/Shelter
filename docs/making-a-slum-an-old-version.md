# Making a slum's data an old version

How to freeze a slum's current data as a past version so a new survey can start
against it. Developer runbook — the page is superuser-only and there is no
self-serve route, so the field team asks a developer to do this.

Background on why it works this way: `docs/slum-data-versions.md`.

---

## 1. What a version actually is

The live tables (`graphs.HouseholdData`, `graphs.SlumData`,
`master.Rapid_Slum_Appraisal`, `component.Component` and the rest) carry **no
version column**. They hold one version at a time: the current one.

Starting a new version therefore means:

1. Every registered table's rows for that slum are copied into
   `survey.SlumVersionBackup`, labelled with the version they belonged to.
2. A new `survey.SlumDataVersion` row is created, with `switched_on` empty.
3. **The live tables are left alone.** The old version stays in use — the
   public map, graphs and exports keep showing it.
4. The first household record whose timestamp is at or after the version's
   `started_on` switches the live household tables over: the old rows are
   deleted there and survive only in the backup.

RIM is never switched automatically. It follows the choice made when the
version is started.

### What you can see afterwards

| Data | Archived? | Viewable in the app? |
|---|---|---|
| RIM (`SlumData` + `Rapid_Slum_Appraisal`) | yes | **yes** — the Reports page offers each version and compares two of them |
| Households, follow-ups, members, toilets, mobilisation | yes | **no** — kept in `SlumVersionBackup`, but nothing in the UI reads them back |
| Components (KML layers) and their metrics | yes | **no** — and they are never cleared automatically |

So household history is preserved but not browsable. Only RIM has version
accessors and a comparison view.

---

## 2. Before you start

Check these for the slum in question:

- **Is a re-survey actually happening?** Starting a version is not reversible
  through the UI. The archive is kept, but the `SlumDataVersion` row and the
  switch are not something the page can undo.
- **Which AVNI location will the new survey arrive under?** If it is a second
  location, map it to the same slum first (§3), or the records will land on a
  different slum or be skipped.
- **What should happen to RIM?** This is the decision the field team needs to
  make with you. See §4.
- **Does the slum have unsynced data pending?** Anything that arrives after the
  checkpoint but before the switch still belongs to the *old* version and is
  re-archived at switch time, so this is safe — but it is worth knowing.

---

## 3. Map the new AVNI location (if there is one)

`/slum-versions/<slum_id>/`

A slum can take data from several AVNI locations, one of which is primary. The
primary one is what the slum-level syncs (RIM, toilets) read.

- **Add location** — paste the AVNI location uuid and its title.
- **Make primary** — moves which location RIM syncs from.

Adding or changing a location **locks the slum's locations** against the nightly
location refresh (`alias_locked`), so the automatic matcher cannot undo your
decision.

If the re-survey was registered as a separate slum rather than a second
location, you want §7 instead.

---

## 4. Choose what happens to RIM

Presented as a radio on the page, and the one thing to settle with the field
team before clicking.

| Choice | What it does | Use when |
|---|---|---|
| **Keep** (default) | RIM is archived and the live RIM is left in place | The new RIM survey will overwrite it when it arrives, and you want the factsheet to keep working meanwhile |
| **Clear and re-sync from a chosen location** | RIM is archived, the live RIM rows are deleted, and the chosen location becomes the primary one | The new RIM is coming from a different AVNI location |
| **Clear and wait for a new sync** | RIM is archived and the live RIM rows are deleted | The old RIM is wrong or superseded and nothing should show until new data arrives |

**Either "clear" option hides the factsheet on the public city map** until a RIM
sync fills the live table again. `master.views.rim_factsheet_available` reports
on live RIM only. The archived factsheet stays readable on the Reports page.

Prefer **Keep** unless there is a reason not to.

---

## 5. Start the version

On `/slum-versions/<slum_id>/`:

1. Pick the RIM choice from §4.
2. Write a **note** — what survey this is, who asked, the date. It is stored on
   the `SlumDataVersion` row and is the only context anyone gets later.
3. Type `START` in the confirmation box.
4. Submit.

You get back how many rows were archived, and a warning if RIM was cleared.

The page then shows the slum as **waiting**: version N+1 exists, and the live
tables still serve version N until the new survey's first household arrives.

### Doing it from a shell instead

```python
from survey import versioning

versioning.start_new_version(
    slum_id,
    user=request.user,                  # or None
    rim_choice=versioning.RIM_KEEP,     # RIM_KEEP / RIM_RESYNC / RIM_CLEAR
    rim_location="<avni-location-uuid>",  # only for RIM_RESYNC
    note="2026 re-survey, requested by <name>",
)
```

### Do not add a version row through Django admin

`SlumDataVersionAdmin` allows it, and it now calls `ensure_backup` so the
snapshot is still taken — but it skips everything else (the RIM choice, the
note prompt, the confirmation). Use the page.

---

## 6. Afterwards

- **Nothing changes publicly yet.** That is intended: the old survey keeps
  serving until the first record of the new one arrives.
- **When the first new household arrives**, the live household tables are
  cleared. Anything that had arrived since the checkpoint is re-archived
  immediately before the delete (`refresh_household_backup`), so nothing is
  lost.
- **Components are never cleared.** The team deletes and re-draws KML layers by
  hand, so the archive is the only record of what the previous survey mapped.
- **The comparison appears** on `/reports/` once the new RIM lands: pick the
  slum, then the two RIM surveys to read against each other.

### Checking the state

```python
from survey import versioning
versioning.describe(slum_id)        # counts, versions, backups, aliases
versioning.rim_backup_versions(slum_id)   # which RIM versions are archived
```

---

## 7. If the re-survey came in as a separate slum

Two slums for one settlement — the old one with history, the new one with the
re-survey. Two tools, both superuser:

- **Merge** (`/slum-versions/<target_id>/`, type `MERGE`) — moves every row from
  the source slum onto the target and **deletes the source**. It refuses while
  anything would collide or any table cannot be read, and writes a JSON dump
  before applying. Irreversible.
- **`adopt_slum_data`** — moves the source's data onto the target without
  deleting the source, replacing components layer by layer. Dry run by default:

  ```bash
  python manage.py adopt_slum_data --from <source_id> --into <target_id>
  python manage.py adopt_slum_data --from <source_id> --into <target_id> --apply
  ```

  It refuses to apply unless the target has a version waiting, since that is
  what makes clearing the target's households safe.

Start the new version on the **target** first, then adopt or merge.

---

## 8. Things that will bite you

- **A slum that was never versioned always writes.** `allows_write` returns
  True when there is no version, which is every slum today. The switch only
  exists once a version has been started.
- **Records older than `started_on` are kept out of the live tables** once the
  switch has happened — they still reach the `survey.Record` mirror, stored
  against their own version. So provider ordering cannot mix versions.
- **The switch currently keys off AVNI's "Last modified at"**, not registration
  time. An edit to an *old* household during the waiting window therefore looks
  like the new survey's first record and triggers the switch early, clearing
  the slum's live household tables. The data survives in the backup, but the
  slum goes blank on the public map until the real re-survey arrives. Known
  issue; see `docs/rim-version-comparison.md` §11.
- **Per-slum sync can be switched off** on the same page. A slum with sync off
  has its incoming records skipped and is named in the nightly digest.
