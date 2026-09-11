"""The nightly Avni sync, previously a manage.py shell heredoc in
deploy/AVNI_DAILY_SYNC.sh plus the manual deploy/sync_rhs.sh mode 1.
"""

import time

LOGGERS = ["graphs.sync_avni_data"]

# (step name, method, args)
STEPS = (
    ("SaveRhsData:Household", "SaveRhsData", ("Household",)),
    ("SaveDailyReportingdata", "SaveDailyReportingdata", ()),
    ("SaveFamilyFactsheetData", "SaveFamilyFactsheetData", ()),
    ("SaveCommunityMobilizationData", "SaveCommunityMobilizationData", ()),
)


def run(recorder):
    from graphs.sync_avni_data import avni_sync

    sync = avni_sync()
    recorder.set_window("modified since {}".format(sync.lastModifiedDateTime()))

    for index, (name, method, args) in enumerate(STEPS):
        if index:
            time.sleep(1)
        with recorder.step(name, loggers=LOGGERS) as step:
            if step.disabled:
                continue
            if not args:
                step.extras["watermark"] = sync.lastModifiedDateTime()
            getattr(sync, method)(*args)
