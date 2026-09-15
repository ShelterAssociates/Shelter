"""A fake job that exercises the recorder end to end without any external call.

    manage.py run_job selftest --no-email   # smoke test on a fresh server
    manage.py run_job selftest              # preview the failure alert
    manage.py send_job_digest               # then preview the digest
"""

import logging

from notification.services import reporting

logger = logging.getLogger("notification.selftest")

FIXTURE = [
    ("Pune", "Ganesh Nagar", "0412", "6f1c2a10-0000-4000-8000-000000000412", None),
    ("Pune", "Ganesh Nagar", "0413", "6f1c2a10-0000-4000-8000-000000000413", None),
    ("Pune", "Ganesh Nagar", "0414", "6f1c2a10-0000-4000-8000-000000000414", KeyError("Date of Survey")),
    ("Thane", "Kisan Nagar", "0087", "6f1c2a10-0000-4000-8000-000000000087", None),
    ("Thane", "Kisan Nagar", "0088", "6f1c2a10-0000-4000-8000-000000000088", ValueError("bad household number")),
    ("Kolhapur", "Rajendra Nagar", "0120", "6f1c2a10-0000-4000-8000-000000000120", None),
    ("Kolhapur", "Rajendra Nagar", "0121", "6f1c2a10-0000-4000-8000-000000000121", None),
    ("Kolhapur", "Rajendra Nagar", "0122", "6f1c2a10-0000-4000-8000-000000000122", None),
]


def run(recorder, params=None):
    recorder.set_window("selftest fixture, no external calls")

    with recorder.step("selftest_records", loggers=[logger.name]) as step:
        step.expect(len(FIXTURE) + 2)
        for city, slum, household, uuid, error in FIXTURE:
            with reporting.record(slum=slum, household=household, city=city, key=uuid):
                if error is not None:
                    logger.error("%s for household %s", error, household)
                    reporting.fail(error)
        step.skip(reason="voided")
        step.skip(reason="empty observations")

    with recorder.step("selftest_clean_step"):
        with reporting.record(city="Panvel", household="0001"):
            pass
