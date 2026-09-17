"""Kept so avni code and jobs keep importing the sync window from here.

The logic is generic and lives in survey/window.py.
"""

from survey.window import (  # noqa: F401
    DAY_START,
    EPOCH,
    FIRST_SYNC_START,
    STRUCTURE_CITIES,
    day_before,
    format_from_date,
    last_successful_run,
    latest_submission,
    window_label,
    window_start,
)
