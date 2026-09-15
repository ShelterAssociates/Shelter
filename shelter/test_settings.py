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
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
