"""Settings for `manage.py test`.

The historic migration chain cannot build a database from scratch (a missing
fixture and an invalid geometry default), so tests create tables straight from
the models. admin_view_permission registers models in a way that needs the real
admin tables, so it is left out.

    python manage.py test --settings=shelter.test_settings --noinput
"""

from shelter.settings import *  # noqa: F401,F403

INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "admin_view_permission"]


class DisableMigrations(dict):
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()
DEBUG = False
# Explicit hosts, as on a real server (utils/checks.py refuses '*' when DEBUG is off).
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
# The developer's local_settings.py may point at prod's BIRT; tests do not use it.
BIRT_REPORT_URL = ""
BIRT_REPORT_CMD = ""
GOOGLE_API_KEY = "test-google-maps-key"
# Failed-login counters off by default; shelter/test_login_throttle.py switches them on.
CACHES = dict(CACHES, auth_throttle={"BACKEND": "django.core.cache.backends.dummy.DummyCache"})
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
