# developer_scripts

Hand-run AVNI maintenance scripts. Nothing in this folder is imported by the
app, wired to a URL, or registered as a job — it only runs when a developer
runs it from the Django shell.

All of them talk to AVNI through `avni.client.client()`, so they share the
process-wide Cognito token, its refresh-on-401, the request timeout and the
throttle. None of them log in on their own.

## Before you reach for these

For a routine, spreadsheet-driven edit, use the **Bulk Update** console
(`avni_console`) instead. It resolves the sheet's columns against the form,
runs a dry run first, writes a `changes.csv` of every old → new value, and
keeps a `BulkUpdate` + `JobRun` audit trail. The scripts here have none of
that: they write to live AVNI immediately and print to stdout.

## What is here

| File | Use |
| --- | --- |
| `subjects.py` | One subject by uuid: read a summary, shift its household number, void it |
| `encounters.py` | Read one encounter by uuid, to see what AVNI actually holds |
| `bulk_observations.py` | Set one observation on many records, from a sqlite run file |
| `one_off_migrations.py` | Two past fixes (missing coordinates, mobilization project), kept for reference |
| `payload.py` | Builds the PUT body AVNI wants for a subject — every subject write uses it |
| `tracker.py` | The sqlite run file: pending rows and the status written back |

## Running them

```
python manage.py shell
```

```python
from developer_scripts import subjects

subjects.summary("efe784a4-aee9-48cc-8bc4-f3cdff50919c")
# {'city': 'Pune', 'slum': '...', 'household_number': '843', ...}

subjects.rename_household("efe784a4-aee9-48cc-8bc4-f3cdff50919c", "0844")
# [RENAME] efe784a4-... 0843 -> 0844
```

```python
from developer_scripts import bulk_observations

bulk_observations.run(
    "/path/to/changes.db", "changes",
    concept="Functioning of the structure", column="fs",
    workers=4,
)
```

## The sqlite run file

`bulk_observations` and `one_off_migrations` read a table with:

- `uuid` — the record to update
- `status` — `1` fetched, `2` fetch failed, `3` written, `4` write failed, `5` errored
- one column per value being written

Only rows that are not yet `3` are picked up, so a run that half failed can be
started again and skips what already went through. Keep the run file outside
the repo — it holds mastersheet-level data and must not be committed.

## Two things to know before writing a subject

**The PUT body is not the GET body.** A GET returns a `location` dict and keeps
the household number inside `observations`. A PUT wants a flat `Address` string
and the household number as a top-level `First name`. Sending a GET body
straight back loses both. `payload.subject_put_body()` does that reshaping —
use it rather than building the body by hand.

**AVNI stores the household number in `First name`.** That is why shifting a
household is `rename_household()`. It does not check whether another household
in the slum already uses the number you are moving to — confirm that first.
