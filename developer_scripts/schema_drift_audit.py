"""Compare every managed model's fields against the real database columns.

Read-only. Run on each environment and diff the reports:
    python manage.py shell -c "exec(open('developer_scripts/schema_drift_audit.py').read())"

Exists because migration files are gitignored, so each environment has its own
history and schema drift is otherwise invisible until a page 500s.
"""

from django.apps import apps
from django.db import connection

FIRST_PARTY = {
    "master", "component", "sponsor", "mastersheet", "graphs", "helpers",
    "notification", "avni", "avni_console", "survey", "photos", "reports",
}

with connection.cursor() as cur:
    cur.execute(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema = current_schema()"
    )
    db = {}
    for table, col in cur.fetchall():
        db.setdefault(table, set()).add(col)

    cur.execute("SELECT app, name FROM django_migrations ORDER BY app, id")
    recorded = {}
    for app, name in cur.fetchall():
        recorded.setdefault(app, []).append(name)

print("DB:", connection.settings_dict["NAME"], "@", connection.settings_dict["HOST"])
print()

problems = 0
for model in apps.get_models():
    app = model._meta.app_label
    if app not in FIRST_PARTY or not model._meta.managed:
        continue
    table = model._meta.db_table
    if table not in db:
        print("MISSING TABLE  %-14s %s" % (app, table))
        problems += 1
        continue
    want = {f.column for f in model._meta.local_fields}
    missing = sorted(want - db[table])
    if missing:
        print("MISSING COLUMN %-14s %-52s %s" % (app, table, missing))
        problems += 1

print()
print("--- migration counts per app (compare across environments) ---")
for app in sorted(FIRST_PARTY):
    names = recorded.get(app, [])
    last = names[-1] if names else "(none)"
    print("   %-14s %3d  last=%s" % (app, len(names), last))

print()
print("TOTAL SCHEMA PROBLEMS:", problems)
