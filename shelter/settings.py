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

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARENT_DIR = os.path.dirname(BASE_DIR)


# ---------------------------------------------------------------------------
# SAFE DEFAULTS
# These are the most restrictive/safe values possible.
# local_settings.py overrides them for each environment.
# If local_settings.py is ever missing a key, production stays safe.
# ---------------------------------------------------------------------------

DEBUG       = False   # overridden to True in local_settings.py for dev
SECRET_KEY  = ''      # MUST be set in local_settings.py
ALLOWED_HOSTS = []    # MUST be set in local_settings.py


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
    'django_extensions',
    'admin_view_permission',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'master',
    'component',
    'sponsor',
    'colorfield',
    'mastersheet',
    'graphs',
    'helpers',
    'reports.apps.ReportsConfig',
    'rest_framework',
    'rest_framework.authtoken',
    'rest_auth',
    'drf_dynamic_fields',
    'widget_tweaks',
)


# ---------------------------------------------------------------------------
# REST FRAMEWORK
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
}


# ---------------------------------------------------------------------------
# ADMIN VIEW PERMISSIONS
# ---------------------------------------------------------------------------

ADMIN_VIEW_PERMISSION_MODELS = [
    'auth.User',
    'master.Survey',
    'master.Slum',
    'master.Rapid_Slum_Appraisal',
]


# ---------------------------------------------------------------------------
# MIDDLEWARE
# ---------------------------------------------------------------------------

MIDDLEWARE = (
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)


# ---------------------------------------------------------------------------
# URL & WSGI
# ---------------------------------------------------------------------------

ROOT_URLCONF      = 'shelter.urls'
WSGI_APPLICATION  = 'shelter.wsgi.application'


# ---------------------------------------------------------------------------
# TEMPLATES
# ---------------------------------------------------------------------------

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
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

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Kolkata'
USE_I18N      = True
USE_L10N      = True
USE_TZ        = True


# ---------------------------------------------------------------------------
# STATIC FILES
#
# STATICFILES_DIRS → source static files inside the codebase (committed to git)
# STATIC_ROOT      → where collectstatic writes files for production serving
#                    (outside the codebase, beside media/, NOT in git)
# STATIC_URL       → URL prefix browsers use to request static files
# ---------------------------------------------------------------------------

STATIC_URL  = '/static/'
SITE_URL    = '/'

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

STATIC_ROOT = os.path.join(PARENT_DIR, 'static_collected/')


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

MEDIA_URL  = '/media/'
MEDIA_ROOT = os.path.join(PARENT_DIR, 'media/')


# ---------------------------------------------------------------------------
# ADMIN
# ---------------------------------------------------------------------------

ADMIN_SITE_HEADER = "Shelter Administration"


# ---------------------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------------------

LOGIN_REDIRECT_URL = 'login_success'