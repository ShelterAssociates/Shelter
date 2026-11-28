"""Rebuild the member summary (MemberDataETL) on demand; the nightly AVNI sync runs it as its last step."""

LOGGERS = ["graphs.member_data_analysis"]


def refresh(from_date=None):
    """Full rebuild; `from_date` is accepted so the nightly step runner can call it like a sync."""
    from graphs import member_data_analysis

    return member_data_analysis.main()


def run(recorder, params=None):
    with recorder.step("member_summary", loggers=LOGGERS) as step:
        if step.disabled:
            return
        totals = refresh()
        if totals["failed_slums"]:
            step.note_error("{} slum(s) failed; see ETLLog".format(totals["failed_slums"]))
