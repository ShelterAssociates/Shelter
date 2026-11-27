"""
Django settings for Shelter project.

This file contains ONLY non-sensitive, environment-agnostic settings.
All secrets, credentials, and environment-specific values live in
local_settings.py which is NEVER committed to git.

Expected folder structure:
    Shelter/                        <-- PARENT_DIR
    ├── app/                        <-- BASE_DIR (this Django project)
    │   ├── manage.py
    │   ├── shelter/
    │   │   ├── settings.py         <-- this file (safe to commit to git)
    │   │   └── local_settings.py   <-- secrets (NEVER commit to git)
    │   └── static/                 <-- source static files (commit to git)
    ├── media/                      <-- user uploaded files (DO NOT commit)
    └── static_collected/           <-- output of collectstatic (DO NOT commit)

.gitignore should contain:
    shelter/local_settings.py
    media/
    static_collected/
"""

import os
import builtins
import inspect
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# MIDDLEWARE
# ---------------------------------------------------------------------------


MIDDLEWARE = (
    "django.middleware.security.SecurityMiddleware",
    "shelter.middleware.ContentSecurityPolicyMiddleware",
    "shelter.middleware.CookieFlagsMiddleware",
    "shelter.middleware.RequestLoggingMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "shelter.middleware.SessionBindingMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
)

# Sessions end after 8 idle hours (renewed on each request) or when the browser closes.
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# No JavaScript reads the CSRF cookie: pages take the token from {% csrf_token %}.
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

# ---------------------------------------------------------------------------
# PATHS
#
# BASE_DIR  → the Django project root (where manage.py lives)
#             e.g. /home/user/Shelter/app   or   /srv/Shelter/app
#             Resolves dynamically — works on any machine, no hardcoding.
#
# PARENT_DIR → one level above the code folder
#              e.g. /home/user/Shelter       or   /srv/Shelter
#              This is where media/ and static_collected/ live,
#              keeping them outside the codebase.
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARENT_DIR = os.path.dirname(BASE_DIR)


# ---------------------------------------------------------------------------
# SAFE DEFAULTS
# These are the most restrictive/safe values possible.
# local_settings.py overrides them for each environment.
# If local_settings.py is ever missing a key, production stays safe.
# ---------------------------------------------------------------------------

DEBUG = False  # overridden to True in local_settings.py for dev
SECRET_KEY = ""  # MUST be set in local_settings.py
ALLOWED_HOSTS = []  # MUST be set in local_settings.py
# This server's https:// address; emailed links are built from it. Set in local_settings.py.
BASE_APP_URL = ""
# Google Maps JavaScript API key for the map pages (it is visible in the browser by design).
# Set per server in local_settings.py; in Google Cloud Console restrict it to this server's
# websites (HTTP referrers) and to the Maps JavaScript API only.
GOOGLE_API_KEY = ""
# Superset as browsers reach it: embedded on the graphs page and allowed by the CSP.
# Each server points at its own (UAT: https://uat-graphs.shelter-associates.org/).
GRAPHS_PUBLIC_URL = "https://graphs.shelter-associates.org/"

# Empty by default so that if local_settings.py ever fails to define this,
# delete_component blocks the delete (no one configured to notify) rather
# than silently deleting with no notification. Set per-environment in
# local_settings.py — dev: developer only; production: developer + GIS.
KML_CHANGE_NOTIFY_EMAILS = []

# Developer address(es) told when a photo export fails. Empty by default so a
# missing local_settings.py can't silently swallow failures -- the runner logs
# loudly if it has nowhere to send them. Set per-environment in
# local_settings.py, same convention as KML_CHANGE_NOTIFY_EMAILS above.
PHOTO_EXPORT_NOTIFY_EMAILS = []

# Refuse to start a photo export that would leave less than this much disk free.
# The server runs close to full, so exports must never be the thing that fills
# it. On refusal the developer is emailed; free space, then re-run from admin.
PHOTO_EXPORT_MIN_FREE_GB = 10

# A photo export still "running" after this long was killed (deploy, restart,
# OOM). The runner marks it failed and reports it.
PHOTO_EXPORT_STUCK_HOURS = 3

# Ceilings for the instant single-household download, which is built in memory
# on the request thread. Anything larger must go through the queued slum export.
PHOTO_INSTANT_MAX_PHOTOS = 60
PHOTO_INSTANT_MAX_MB = 80

# Extra groups allowed to download photos, on top of superusers. Empty means
# superuser-only, which is the intent -- bulk photo exports can contain Aadhaar
# card images.
PHOTO_DOWNLOAD_GROUPS = []

# Fallback recipients for scheduled-job digests/alerts, used only when the
# notification address book has no active rows for the purpose yet.
JOB_NOTIFY_FALLBACK_EMAILS = []

# With DEBUG on, send_email() delivers every mail ONLY to the "dev_redirect"
# contacts in the address book; this is the fallback when that purpose is empty.
# If both are empty, sending is refused so a dev run can never reach real people.
EMAIL_DEV_REDIRECT_TO = []

# Directory under MEDIA_ROOT holding per-run detail reports. Must stay in sync with
# EXPORT_DIRS in deploy/CLEANUP_GENERATED_FILES.sh, which reaps it after 24h.
JOB_REPORT_DIR_NAME = "job_reports"

# Detail reports larger than this are attached truncated (head+tail).
JOB_REPORT_MAX_ATTACH_BYTES = 5 * 1024 * 1024

# A JobRun still "running" after this long was killed; the digest marks it crashed.
JOB_RUN_STUCK_HOURS = 6

# AVNI sync console (avni_console app). Override in local_settings.py.
# Groups (by name) allowed to open the console and queue syncs; superusers always can.
AVNI_SYNC_GROUPS = []
# Groups additionally allowed to push bulk updates INTO AVNI. Empty = superusers only.
AVNI_WRITE_GROUPS = []
# Rows per uploaded Excel on this host (production keeps it small; raise locally).
AVNI_BULK_MAX_ROWS = 50
# Parallel workers for a bulk update (production 1; raise locally).
AVNI_BULK_WORKERS = 1
# Hour (IST) at which queued dashboard refreshes run.
AVNI_DASHBOARD_QUEUE_HOUR = 1
# Where uploaded bulk-update files are kept (under MEDIA_ROOT); never auto-cleaned.
AVNI_BULK_UPLOAD_DIR_NAME = "avni_bulk_updates"
# Timeout for every AVNI HTTP call, seconds.
AVNI_REQUEST_TIMEOUT = 60
# Shared key the Shelter build of the Avni mobile app sends (X-Avni-Gis-Key)
# to the map endpoints in component/avni_map.py. Empty = endpoints refuse
# with 503. Set a long random value per environment in local_settings.py and
# the same value in the app's config.
AVNI_GIS_API_KEY = ""
# Form cache older than this counts as stale in the console.
AVNI_FORM_CACHE_MAX_AGE_HOURS = 48
# Subject explorer: how many subjects one page previews live from AVNI. The
# sync itself has no cap: every uuid pasted or uploaded is queued and runs in
# the background like any other console job.
AVNI_SUBJECT_PREVIEW_MAX_IDS = 25

# Design Studio (design_studio app): DIGIPIN and Plus Code plates and stickers. Override in local_settings.py.
# Groups allowed to make plates; superusers always can. Empty = superusers only.
DESIGN_STUDIO_GROUPS = ["design_studio"]
# Groups allowed to create and edit plate templates. Empty = superusers only.
DESIGN_STUDIO_TEMPLATE_GROUPS = []
DESIGN_STUDIO_MAX_ROWS = 15000
DESIGN_STUDIO_MAX_UPLOAD_MB = 10
DESIGN_STUDIO_MAX_ASSET_MB = 5
# Uploaded Excel of a confirmed batch is kept this long so it can be generated again.
DESIGN_STUDIO_UPLOAD_KEEP_DAYS = 180
# Drafts never confirmed are deleted (row and file) after this many days.
DESIGN_STUDIO_DRAFT_KEEP_DAYS = 7
DESIGN_STUDIO_MIN_FREE_DISK_GB = 5
# Folders under MEDIA_ROOT; nginx denies /media/plate_* and the exports name must
# match EXPORT_DIRS in deploy/CLEANUP_GENERATED_FILES.sh.
DESIGN_STUDIO_EXPORT_DIR_NAME = "design_exports"
DESIGN_STUDIO_UPLOAD_DIR_NAME = "design_uploads"
DESIGN_STUDIO_ASSET_DIR_NAME = "design_assets"
DESIGN_STUDIO_FONT_DIR_NAME = "design_fonts"
# Hosts a template's QR link may point to.
DESIGN_STUDIO_QR_ALLOWED_HOSTS = ["dac.indiapost.gov.in", "www.google.com"]

# ---------------------------------------------------------------------------
# SURVEY DATA CORE
# ---------------------------------------------------------------------------

# The survey tool the core store reads through. Swap this one line to move to
# another tool (e.g. "kobo.provider.KoboProvider"); survey/* stays untouched.
SURVEY_PROVIDER = "avni.provider.AvniProvider"

# Use BigAutoField by default to avoid Django warnings about auto-created PK types
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# IMPORT LOCAL SETTINGS
# Done early so that DEBUG is available for the print guard below,
# and so that any setting here can be overridden by local_settings.py.
# Imported ONCE — do not add a second import anywhere in this file.
# ---------------------------------------------------------------------------

from shelter.local_settings import *  # noqa

# ---------------------------------------------------------------------------
# DEBUG PRINT HELPER
# Overrides built-in print() to include file name and line number.
# Only active in development (DEBUG=True). Never runs in production.
# ---------------------------------------------------------------------------

if DEBUG:
    _old_print = print

    def _debug_print(*args, **kwargs):
        frame = inspect.currentframe().f_back
        location = f"{frame.f_code.co_filename}:{frame.f_lineno}"
        _old_print(f"[{location}]", *args, **kwargs)

    builtins.print = _debug_print


# ---------------------------------------------------------------------------
# INSTALLED APPS
# ---------------------------------------------------------------------------

INSTALLED_APPS = (
    "admin_view_permission",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "shelter.apps.StaticFilesConfig",
    "django.contrib.gis",
    "master",
    "component",
    "sponsor",
    "colorfield",
    "mastersheet",
    "graphs",
    "helpers",
    "notification.apps.NotificationConfig",
    "avni.apps.AvniConfig",
    "avni_console.apps.AvniConsoleConfig",
    "survey.apps.SurveyConfig",
    "photos",
    "design_studio.apps.DesignStudioConfig",
    "reports.apps.ReportsConfig",
    "rest_framework",
    "rest_framework.authtoken",
    "rest_auth",
    "drf_dynamic_fields",
    "widget_tweaks",
)
# INSTALLED_APPS = (
#     'admin_view_permission',
#     'django.contrib.admin',
#     'django.contrib.auth',
#     'django.contrib.contenttypes',
#     'django.contrib.sessions',
#     'django.contrib.messages',
#     'django.contrib.staticfiles',
#     'django.contrib.gis',
#      #'south',
#      'master',
#      'component',
#       #'Filter',
#      'sponsor',
#      'colorfield',
#      'mastersheet',
#      'graphs',
#     'rest_framework',
#     'rest_framework.authtoken',
#     'rest_auth',
# )


# ---------------------------------------------------------------------------
# REST FRAMEWORK
# ---------------------------------------------------------------------------

# Sent on every response by shelter.middleware.ContentSecurityPolicyMiddleware, which adds a
# per-request nonce to script-src: inline <script> tags need nonce="{{ csp_nonce }}" and inline
# event handlers are not allowed. Images may come from any https host (S3 survey photos, AVNI,
# map tiles). Set CSP_REPORT_ONLY = True to only report.
CSP_REPORT_ONLY = False
CSP_REPORT_URI = "/csp-report/"
CSP_POLICY = {
    "default-src": ["'self'"],
    "script-src": [
        "'self'", "https://maps.googleapis.com", "https://maps.gstatic.com", "https://cdn.jsdelivr.net",
        "https://cdn.datatables.net", "https://cdnjs.cloudflare.com",
    ],
    "style-src": [
        "'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdn.jsdelivr.net",
        "https://cdnjs.cloudflare.com", "https://cdn.datatables.net",
    ],
    "font-src": ["'self'", "data:", "https://fonts.gstatic.com"],
    "img-src": ["'self'", "data:", "blob:", "https:"],
    "connect-src": [
        "'self'", "https://maps.googleapis.com", "https://s3.ap-south-1.amazonaws.com",
        "https://*.s3.ap-south-1.amazonaws.com", "https://*.s3.amazonaws.com",
        # 3D slum view (static/js/map3d.js): MapLibre glyphs and satellite tiles
        "https://demotiles.maplibre.org", "https://server.arcgisonline.com",
    ],
    "frame-src": ["'self'", "{0.scheme}://{0.netloc}".format(urlparse(GRAPHS_PUBLIC_URL))],
    "worker-src": ["'self'", "blob:"],
    "object-src": ["'none'"],
    "base-uri": ["'self'"],
    "form-action": ["'self'"],
    "frame-ancestors": ["'self'"],
}

AUTHENTICATION_BACKENDS = ["shelter.auth_throttle.ThrottledModelBackend"]

# Failed sign-in counters must be shared by all gunicorn workers, so they live on disk.
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "auth_throttle": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": os.path.join(PARENT_DIR, "cache", "auth_throttle"),
    },
    # Design Studio template previews (sample-row pictures only), shared by every worker.
    "design_preview": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": os.path.join(PARENT_DIR, "cache", "design_preview"),
        "TIMEOUT": 30 * 24 * 3600,
        "OPTIONS": {"MAX_ENTRIES": 500},
    },
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.AllowAny",),
    # The HTML ("browsable") API only for development; servers answer JSON.
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",)
    + (("rest_framework.renderers.BrowsableAPIRenderer",) if DEBUG else ()),
}


# ---------------------------------------------------------------------------
# ADMIN VIEW PERMISSIONS
# ---------------------------------------------------------------------------

ADMIN_VIEW_PERMISSION_MODELS = [
    "auth.User",
    "master.Survey",
    "master.Slum",
    "master.Rapid_Slum_Appraisal",
]




# ---------------------------------------------------------------------------
# URL & WSGI
# ---------------------------------------------------------------------------

ROOT_URLCONF = "shelter.urls"
WSGI_APPLICATION = "shelter.wsgi.application"


# ---------------------------------------------------------------------------
# TEMPLATES
# ---------------------------------------------------------------------------

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "shelter.context_processors.csp_nonce",
                "shelter.context_processors.google_api_key",
            ],
        },
    },
]


# ---------------------------------------------------------------------------
# DATABASE
# Full DATABASES dict is defined in local_settings.py (credentials differ
# per environment). Only the PostGIS version hint is safe to put here.
# ---------------------------------------------------------------------------

POSTGIS_VERSION = (2, 0, 3)


# ---------------------------------------------------------------------------
# INTERNATIONALISATION
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_L10N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# STATIC FILES
#
# STATICFILES_DIRS → source static files inside the codebase (committed to git)
# STATIC_ROOT      → where collectstatic writes files for production serving
#                    (outside the codebase, beside media/, NOT in git)
# STATIC_URL       → URL prefix browsers use to request static files
# ---------------------------------------------------------------------------

STATIC_URL = "/static/"
SITE_URL = "/"

STATICFILES_DIRS = (os.path.join(BASE_DIR, "static"),)

STATIC_ROOT = os.path.join(PARENT_DIR, "static_collected/")


# ---------------------------------------------------------------------------
# MEDIA FILES
#
# MEDIA_ROOT → where Django saves user-uploaded files.
#              Sits beside the codebase (not inside it) so uploads are never
#              accidentally committed or wiped by a git pull.
#              Fully dynamic — derived from PARENT_DIR so it works on any
#              machine without hardcoding paths.
#
#              Local dev : ~/Shelter/media/
#              Server    : /srv/Shelter/media/
#
# MEDIA_URL  → URL prefix browsers use to request uploaded files
# ---------------------------------------------------------------------------

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(PARENT_DIR, "media/")


# ---------------------------------------------------------------------------
# ADMIN
# ---------------------------------------------------------------------------

ADMIN_SITE_HEADER = "Shelter Administration"


# ---------------------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------------------

LOGIN_REDIRECT_URL = "login_success"

# Self-service reset is retired, so every password is typed by the administrator
# into the admin's set-password form, which runs these. create_user() in code
# bypasses them, and existing weak passwords stay valid until changed.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# LOGGING
#
# All logs go to PARENT_DIR/logs/app.log (outside the codebase, like
# media/ and static_collected/), plus console output for `runserver`
# and gunicorn's own stdout/stderr capture.
# ---------------------------------------------------------------------------

LOG_DIR = os.path.join(PARENT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} [{levelname}] {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": os.path.join(LOG_DIR, "app.log"),
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "request_logger": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
