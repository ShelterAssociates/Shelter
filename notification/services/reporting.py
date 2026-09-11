"""Records what a scheduled job did, per step and per city.

Call start() to open a run, run.step() for each unit of work, and step.record()
around each record processed. Every helper is a no-op when no run is active, so
the same sync code stays usable from web requests.
"""

import logging
import os
import socket
import threading
import traceback
from contextlib import contextmanager

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

MAX_SAMPLE_FAILURES = 50
UNKNOWN_CITY = "Unknown"

_state = threading.local()


def _describe(exc):
    if isinstance(exc, BaseException):
        return "{}: {}".format(type(exc).__name__, exc)
    return str(exc)


def fail(exc, detail=None):
    """Mark the current record failed without raising. No-op outside a run."""
    reason = _describe(exc)
    if detail is not None:
        reason = "{} ({})".format(reason, detail)
    record = getattr(_state, "record", None)
    if record is not None:
        record.mark_failed(reason)
        return
    step = getattr(_state, "step", None)
    if step is not None:
        step.note_error(reason)


def active_run():
    return getattr(_state, "run", None)


class _Record(object):
    __slots__ = ("slum", "household", "key", "city", "city_id", "failed", "reason")

    def __init__(self, slum, household, key, city=None, city_id=None):
        self.slum = slum
        self.household = household
        self.key = key
        self.city = city
        self.city_id = city_id
        self.failed = False
        self.reason = ""

    def mark_failed(self, reason):
        if not self.failed:
            self.failed = True
            self.reason = reason


class _CityResolver:
    """slum name -> (city_id, city_name), cached for the life of a run."""

    def __init__(self):
        self._cache = {}

    def resolve(self, slum_name):
        if slum_name in self._cache:
            return self._cache[slum_name]
        result = (None, UNKNOWN_CITY)
        if slum_name:
            try:
                from master.models import Slum

                row = (
                    Slum.objects.filter(name=slum_name)
                    .values_list(
                        "electoral_ward__administrative_ward__city__id",
                        "electoral_ward__administrative_ward__city__name__city_name",
                    )
                    .first()
                )
                if row and row[0]:
                    result = (row[0], row[1] or UNKNOWN_CITY)
            except Exception as exc:
                logger.warning("City lookup failed for slum %s: %s", slum_name, exc)
        self._cache[slum_name] = result
        return result


class _DetailWriter:
    """Appends one line per record so a crash still leaves a readable file."""

    def __init__(self, path):
        self.path = path
        self._fh = None
        try:
            directory = os.path.dirname(path)
            if not os.path.isdir(directory):
                os.makedirs(directory)
            self._fh = open(path, "a")
        except Exception as exc:
            logger.error("Cannot open job detail file %s: %s", path, exc)

    def line(self, status, step_name, city, slum, household, reason="", key=None):
        if self._fh is None:
            return
        try:
            self._fh.write(
                "{}  {:<5} {:<12} {:<28} {:<10} {:<36} {:<28} {}\n".format(
                    timezone.localtime().strftime("%Y-%m-%d %H:%M:%S"),
                    status,
                    (city or "-")[:12],
                    (slum or "-")[:28],
                    (household or "-")[:10],
                    (str(key) if key else "-")[:36],
                    step_name[:28],
                    reason,
                )
            )
        except Exception:
            pass

    def header(self, text):
        if self._fh is None:
            return
        try:
            self._fh.write("{}\n".format(text))
        except Exception:
            pass

    def flush(self):
        if self._fh is not None:
            try:
                self._fh.flush()
            except Exception:
                pass

    def close(self):
        if self._fh is not None:
            try:
                self._fh.close()
            except Exception:
                pass
            self._fh = None


class _ErrorCapture(logging.Handler):
    """Catches logger.error() calls the sync code swallows and attributes them."""

    def __init__(self, step):
        logging.Handler.__init__(self, level=logging.ERROR)
        self.step = step

    def emit(self, record):
        try:
            try:
                message = record.getMessage()
            except Exception:
                message = "{!r} {!r}".format(record.msg, record.args)
            current = getattr(_state, "record", None)
            if current is not None:
                current.mark_failed(message)
            else:
                self.step.note_error(message)
        except Exception:
            pass


class StepRecorder(object):
    def __init__(self, run, name, order, loggers=None):
        from notification.models import JobStep

        self.run = run
        self.name = name
        self.disabled = name in run.disabled_steps
        self.model = JobStep.objects.create(run=run.model, name=name, order=order)
        self.expected = 0
        self.total = 0
        self.ok = 0
        self.failed = 0
        self.skipped = 0
        self.error = None
        self._cities = {}
        self._failures = []
        self._logger_names = list(loggers or [])
        self._handler = _ErrorCapture(self)
        self._attached = []

    def attach(self):
        for name in self._logger_names:
            try:
                target = logging.getLogger(name)
                target.addHandler(self._handler)
                self._attached.append(target)
            except Exception:
                pass

    def detach(self):
        for target in self._attached:
            try:
                target.removeHandler(self._handler)
            except Exception:
                pass
        self._attached = []

    def expect(self, count):
        """Total records the source reports, so skipped can be counted honestly."""
        try:
            self.expected = int(count)
        except (TypeError, ValueError):
            self.expected = 0

    def note_error(self, message):
        """A step-level error with no record to attribute it to."""
        if self.error is None:
            self.error = message

    def skip(self, slum=None, reason=""):
        self.skipped += 1
        city_name = None
        if slum:
            city_id, city_name = self.run.cities.resolve(slum)
            self._bucket(city_name, city_id)["skipped"] += 1
        self.run.writer.line("SKIP", self.name, city_name, slum, None, reason)

    @contextmanager
    def record(self, slum=None, household=None, key=None, city=None, city_id=None):
        item = _Record(slum, household, key, city, city_id)
        previous = getattr(_state, "record", None)
        _state.record = item
        self.total += 1
        try:
            yield item
        except Exception as exc:
            item.mark_failed(_describe(exc))
            raise
        finally:
            _state.record = previous
            self._close(item)

    def _bucket(self, city_name, city_id):
        if city_name not in self._cities:
            self._cities[city_name] = {
                "city_id": city_id,
                "ok": 0,
                "failed": 0,
                "skipped": 0,
            }
        return self._cities[city_name]

    def _close(self, item):
        if item.city:
            city_id, city_name = item.city_id, item.city
        else:
            city_id, city_name = self.run.cities.resolve(item.slum)
        bucket = self._bucket(city_name, city_id)
        if item.failed:
            self.failed += 1
            bucket["failed"] += 1
            if len(self._failures) < MAX_SAMPLE_FAILURES:
                self._failures.append(
                    {
                        "city": city_name,
                        "slum": item.slum or "",
                        "household": item.household or "",
                        "reason": item.reason,
                    }
                )
            self.run.writer.line(
                "FAIL", self.name, city_name, item.slum, item.household,
                item.reason, key=item.key,
            )
        else:
            self.ok += 1
            bucket["ok"] += 1
            self.run.writer.line(
                "OK", self.name, city_name, item.slum, item.household, key=item.key
            )

    def finish(self, status=None):
        from notification.models import JobStepCityStat

        self.detach()
        if self.disabled and status is None:
            status = "disabled"
        if self.expected > self.total:
            self.skipped += self.expected - self.total
        if status is None:
            if self.error and not self.total:
                status = "failed"
            elif self.failed and self.ok:
                status = "partial"
            elif self.failed:
                status = "failed"
            else:
                status = "success"

        self.model.status = status
        self.model.finished_on = timezone.now()
        self.model.records_total = self.total
        self.model.records_ok = self.ok
        self.model.records_failed = self.failed
        self.model.records_skipped = self.skipped
        self.model.error = self.error
        self.model.sample_failures = self._failures
        self.model.save()

        for city_name, data in self._cities.items():
            JobStepCityStat.objects.create(
                step=self.model,
                city_id=data["city_id"],
                city_name=city_name,
                records_ok=data["ok"],
                records_failed=data["failed"],
                records_skipped=data["skipped"],
            )
        self.run.writer.flush()


class RunRecorder(object):
    def __init__(self, job_key, trigger="cron", definition=None, parent_run=None):
        from notification.models import JobRun

        self.job_key = job_key
        self.definition = definition
        self.model = JobRun.objects.create(
            job=definition,
            job_key=job_key,
            parent_run=parent_run,
            trigger=trigger,
            hostname=socket.gethostname()[:200],
            pid=os.getpid(),
        )
        self.cities = _CityResolver()
        self.disabled_steps = definition.disabled_steps() if definition else set()
        self.writer = _DetailWriter(self._detail_path())
        self.model.detail_file_path = self.writer.path
        self.model.save(update_fields=["detail_file_path"])
        self.steps = []
        self.writer.header(
            "columns: time | status | city | slum | household | avni uuid | step | reason"
        )
        self.writer.header(
            "Shelter job report: {} (run #{}) started {}".format(
                job_key,
                self.model.pk,
                timezone.localtime(self.model.started_on).strftime("%Y-%m-%d %H:%M:%S"),
            )
        )
        _state.run = self

    def _detail_path(self):
        directory = getattr(settings, "JOB_REPORT_DIR_NAME", "job_reports")
        stamp = timezone.localtime().strftime("%Y%m%d_%H%M")
        return os.path.join(
            settings.MEDIA_ROOT,
            directory,
            str(self.model.pk),
            "{}_{}.txt".format(self.job_key, stamp),
        )

    def set_window(self, label):
        self.model.window_label = (label or "")[:200]
        self.model.save(update_fields=["window_label"])
        self.writer.header("Window: {}".format(label))

    @contextmanager
    def step(self, name, loggers=None):
        """Yields a StepRecorder. Check `.disabled` and skip the body when set."""
        self._register_step(name)
        recorder = StepRecorder(self, name, len(self.steps), loggers)
        self.steps.append(recorder)
        previous = getattr(_state, "step", None)
        _state.step = recorder
        recorder.attach()
        self.writer.header(
            "--- step: {}{} ---".format(name, " (disabled in admin)" if recorder.disabled else "")
        )
        try:
            yield recorder
        except Exception as exc:
            recorder.note_error(_describe(exc))
            recorder.finish(status="failed")
            raise
        else:
            recorder.finish()
        finally:
            _state.step = previous
            recorder.detach()

    def _register_step(self, name):
        """First sighting of a step creates its admin switch, enabled."""
        if self.definition is None:
            return
        from notification.models import JobStepConfig

        JobStepConfig.objects.get_or_create(
            job=self.definition, step_name=name, defaults={"order": len(self.steps)}
        )

    def finish(self, status=None, error=None):
        total = sum(s.total for s in self.steps)
        ok = sum(s.ok for s in self.steps)
        failed = sum(s.failed for s in self.steps)
        if status is None:
            statuses = [s.model.status for s in self.steps if s.model.status != "disabled"]
            if error or "failed" in statuses:
                status = "partial" if ok else "failed"
            elif "partial" in statuses:
                status = "partial"
            else:
                status = "success"

        self.model.status = status
        self.model.finished_on = timezone.now()
        self.model.records_total = total
        self.model.records_ok = ok
        self.model.records_failed = failed
        if error:
            self.model.error = error
        self.model.save()
        self.writer.header(
            "Finished {} - {} ok, {} failed, {} total".format(
                status, ok, failed, total
            )
        )
        self.writer.close()
        if getattr(_state, "run", None) is self:
            _state.run = None
        return self.model

    def crash(self, exc):
        return self.finish(status="crashed", error=traceback.format_exc())


def start(job_key, trigger="cron", definition=None, parent_run=None):
    return RunRecorder(job_key, trigger, definition, parent_run)


@contextmanager
def record(slum=None, household=None, key=None, city=None, city_id=None):
    """Record one item against the active step. No-op outside a run."""
    step = getattr(_state, "step", None)
    if step is None:
        yield None
        return
    with step.record(
        slum=slum, household=household, key=key, city=city, city_id=city_id
    ) as item:
        yield item


def expect(count):
    step = getattr(_state, "step", None)
    if step is not None:
        step.expect(count)


def skip(slum=None, reason=""):
    step = getattr(_state, "step", None)
    if step is not None:
        step.skip(slum=slum, reason=reason)
