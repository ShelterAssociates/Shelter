"""The sqlite run file the bulk scripts read, and the status they write back.

The table needs a `uuid` column, a `status` column, and whichever columns hold
the new values. Statuses:

    1 fetched   2 fetch failed   3 written   4 write failed   5 errored

Only rows that are not yet 3 are picked up, so a run that half failed can be
started again and will skip what already went through.
"""

import sqlite3

FETCHED = 1
FETCH_FAILED = 2
WRITTEN = 3
WRITE_FAILED = 4
ERRORED = 5


def connect(db_path):
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def pending(connection, table):
    """Every row still to do, as plain dicts."""
    cursor = connection.execute('SELECT * FROM {} WHERE status != ?'.format(quoted(table)), (WRITTEN,))
    return [dict(row) for row in cursor.fetchall()]


def set_status(connection, table, uuid, status):
    connection.execute('UPDATE {} SET status = ? WHERE uuid = ?'.format(quoted(table)), (status, uuid))


def quoted(table):
    """sqlite cannot parameterize a table name, so check it before interpolating."""
    if not table or not table.replace("_", "").isalnum():
        raise ValueError("not a plain table name: {!r}".format(table))
    return '"{}"'.format(table)
