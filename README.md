# Shelter WebApp

Django-based geographic information system for Shelter Associates — managing survey data, slum mapping, resident health records, sponsor tracking, and field reporting across India.

---

## Table of Contents

1. [Tech Stack](#tech-stack)
2. [Folder Structure](#folder-structure)
3. [Prerequisites](#prerequisites)
4. [First-Time Setup](#first-time-setup)
5. [local_settings.py — REQUIRED](#local_settingspy--required)
6. [Database Setup](#database-setup)
7. [Running the App](#running-the-app)
8. [Production Deployment](#production-deployment)
9. [Settings Architecture](#settings-architecture)
10. [Key Configuration Reference](#key-configuration-reference)
11. [Git Workflow](#git-workflow)
12. [Troubleshooting](#troubleshooting)

---

## Tech Stack

| Component   | Details                                              |
|-------------|------------------------------------------------------|
| Framework   | Django 3.0.7 with GeoDjango (PostGIS backend)        |
| Database    | PostgreSQL + PostGIS 2.0.3                           |
| Auth        | Session + Token (rest_framework + rest_auth)         |
| APIs        | Django REST Framework 3.11 + drf-dynamic-fields      |
| Reports     | BIRT Report Engine + custom PDF microservice         |
| Graphs      | Apache Superset (embedded dashboards)                |
| Field Sync  | Avni Project integration                             |
| Python Env  | Conda (`pyenv36`) or virtualenv                      |

---

## Folder Structure

The project uses a **two-level structure** — the Django code lives inside a parent folder, and `media/` and `static_collected/` sit beside it (not inside the codebase). This keeps uploaded files out of git and makes deployment paths consistent.

```
Shelter/                         ← PARENT_DIR  (~/Shelter on local, /srv/Shelter on server)
├── app/                         ← BASE_DIR    (your Django project root)
│   ├── manage.py
│   ├── requirements.txt
│   ├── shelter/
│   │   ├── settings.py          ← safe to commit  ✅
│   │   ├── local_settings.py    ← NEVER commit  ❌  (see Section 5)
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── master/
│   ├── component/
│   ├── sponsor/
│   ├── graphs/
│   ├── helpers/
│   ├── reports/
│   ├── mastersheet/
│   ├── static/                  ← source static files (committed to git)
│   └── templates/
├── media/                       ← user-uploaded files  (NOT in git)
└── static_collected/            ← output of collectstatic  (NOT in git)
```

**Why media/ is outside the codebase:**  
A `git pull` on the server will never accidentally delete uploaded files. The path is fully dynamic — `settings.py` computes it from `PARENT_DIR = os.path.dirname(BASE_DIR)`, so it works on any machine without hardcoding.

---

## Prerequisites

Install the following before setting up the project:

- **Python 3.6** (via Conda env `pyenv36` or virtualenv)
- **PostgreSQL 10+** with **PostGIS 2.0.3** extension
- **GDAL / GEOS / PROJ** libraries (required by GeoDjango)
- **Git**

### Install system dependencies (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y \
    postgresql postgresql-contrib postgis \
    gdal-bin libgdal-dev \
    libgeos-dev libproj-dev \
    python3-dev build-essential
```

### Install Python dependencies

```bash
# With conda
conda activate pyenv36
pip install -r requirements.txt

# With virtualenv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## First-Time Setup

Run these commands after cloning the repository:

```bash
# 1. Clone and navigate
git clone <repo-url> ~/Shelter/app
cd ~/Shelter/app

# 2. Create the media and static_collected folders beside the codebase
mkdir -p ~/Shelter/media
mkdir -p ~/Shelter/static_collected

# 3. Activate your Python environment
conda activate pyenv36        # or: source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create your local_settings.py  ← SEE SECTION 5 BELOW
cp shelter/local_settings.example.py shelter/local_settings.py
# Then edit local_settings.py with your actual credentials

# 6. Run database migrations
python manage.py migrate

# 7. Collect static files (optional for local dev)
python manage.py collectstatic --noinput

# 8. Create a superuser
python manage.py createsuperuser

# 9. Start the development server
python manage.py runserver
```

---

## local_settings.py — REQUIRED

> ⚠️ **This file is not included in the repository and will never be committed to git.**  
> You must create it yourself before the application will start.  
> If you do not have the credentials, **contact the system administrator**.

### How to create it

Copy the example template:

```bash
cp shelter/local_settings.example.py shelter/local_settings.py
```

Then open `shelter/local_settings.py` and fill in every value marked `CHANGE_ME`.

### What goes in local_settings.py

This file contains everything that differs between environments — credentials, debug flags, API keys, and database config. **Nothing in this file should ever be pasted into settings.py or committed to git.**

```python
# shelter/local_settings.py

# ── Core Django ──────────────────────────────────────────────────────────────
# Generate a new secret key with:
#   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY = 'CHANGE_ME'

DEBUG = True                          # Set to False on production
ALLOWED_HOSTS = ['*']                 # Set to ['shelter-associates.org'] on production

# ── Database ─────────────────────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME':   'CHANGE_ME',        # your local DB name
        'USER':   'CHANGE_ME',        # your PostgreSQL username
        'PASSWORD': 'CHANGE_ME',
        'HOST':   'localhost',
        'OPTIONS': { 'options': '-c timezone=UTC' }
    }
}

# ── Email ────────────────────────────────────────────────────────────────────
EMAIL_BACKEND     = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS     = True
EMAIL_HOST        = 'smtp.gmail.com'
EMAIL_PORT        = 587
EMAIL_HOST_USER   = 'CHANGE_ME@gmail.com'
EMAIL_HOST_PASSWORD = 'CHANGE_ME'
SERVER_EMAIL      = EMAIL_HOST_USER

# ── PDF Microservice ──────────────────────────────────────────────────────────
PDF_SERVICE_URL   = 'http://127.0.0.1:9000/generate-pdf'   # local
PDF_FETCH_URL     = 'http://127.0.0.1:9000/fetch-pdf'      # local
PDF_SECRET_KEY    = 'CHANGE_ME'
INTERNAL_TEAM_SECRET = 'CHANGE_ME'

# ── BIRT Reports ─────────────────────────────────────────────────────────────
BIRT_REPORT_CMD = 'sh /opt/birt-runtime/ReportEngine/genReport.sh -f PDF -o {} -p key={} /path/to/reports/FFReport.rptdesign'
BIRT_REPORT_URL = 'http://report.shelter-associates.org/'

# ── External APIs ─────────────────────────────────────────────────────────────
GOOGLE_API_KEY       = 'CHANGE_ME'
CIPHER_KEY           = 'CHANGE_ME'
API_BASE_URL         = 'http://127.0.0.1:8000'   # local
BASE_APP_URL         = 'http://127.0.0.1:8000'   # local

# ── Avni Integration ──────────────────────────────────────────────────────────
AVNI_URL      = 'https://app.avniproject.org/'
AVNI_USERNAME = 'CHANGE_ME'
AVNI_PASSWORD = 'CHANGE_ME'

# ── Superset / Graphs ─────────────────────────────────────────────────────────
GRAPHS_URL = 'http://127.0.0.1:8088/'
GRAPHS_BUILD_URL = GRAPHS_URL + 'login/?username=%s&redirect=/superset/dashboard/%s/?standalone=true'
GRAPH_DETAILS = {
    'community_mobilization': ('community_mobilization', 'CHANGE_ME', 'CHANGE_ME'),
    'toilet_construction':    ('toilet_construction',    'CHANGE_ME', 'CHANGE_ME'),
    'rhs_rhsfollowup':        ('rhs_rhsfollowup',        'CHANGE_ME', 'CHANGE_ME'),
}
```

### .gitignore — verify these lines are present

```
shelter/local_settings.py
media/
static_collected/
```

---

## Database Setup

### Create the database locally

```bash
# Switch to postgres user
sudo -u postgres psql

-- Inside psql:
CREATE USER shelter WITH PASSWORD 'your_password';
CREATE DATABASE shelter_local OWNER shelter;
\c shelter_local
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;
\q
```

### Restore from a backup

```bash
# Restore .backup file
pg_restore -U shelter -d shelter_local /path/to/backup.backup

# Restore .sql file
psql -U shelter -d shelter_local < /path/to/backup.sql
```

### Run migrations after restore

```bash
python manage.py migrate --run-syncdb
```

---

## Running the App

### Development server

```bash
conda activate pyenv36
cd ~/Shelter/app
python manage.py runserver
# Visit http://127.0.0.1:8000
```

### Collect static files (run whenever static files change)

```bash
python manage.py collectstatic --noinput
```

### Open Django shell

```bash
python manage.py shell_plus    # requires django-extensions
```

---

## Production Deployment

### On the server, the folder structure mirrors local

```
/srv/Shelter/
├── app/               ← Django code (git pull goes here)
├── media/             ← uploaded files
└── static_collected/  ← collectstatic output
```

### Steps to deploy

```bash
# 1. SSH into server
ssh user@shelter-associates.org

# 2. Pull latest code
cd /srv/Shelter/app
git pull origin main

# 3. Install/update dependencies
pip install -r requirements.txt

# 4. Run migrations
python manage.py migrate

# 5. Collect static files
python manage.py collectstatic --noinput

# 6. Restart the application server
sudo systemctl restart gunicorn    # or your service name
sudo systemctl reload nginx
```

### Production local_settings.py differences

On the server, `local_settings.py` must have:

```python
DEBUG = False
ALLOWED_HOSTS = ['shelter-associates.org', 'www.shelter-associates.org']
API_BASE_URL  = 'https://shelter-associates.org'
BASE_APP_URL  = 'https://shelter-associates.org'

# Use production PDF service URLs (not 127.0.0.1)
PDF_SERVICE_URL = 'https://shelter-associates.org/pdf/generate-pdf'
PDF_FETCH_URL   = 'https://shelter-associates.org/pdf/fetch-pdf'

# Use production Superset URL
GRAPHS_URL = 'http://graphs.shelter-associates.org/'

# Generate a fresh SECRET_KEY — never reuse the dev key
SECRET_KEY = '<new-production-key>'
```

Generate a fresh secret key for production:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Settings Architecture

Settings are intentionally split across two files:

| File | Committed to git? | Contains |
|------|:-----------------:|----------|
| `shelter/settings.py` | ✅ Yes | Installed apps, middleware, templates config, path logic, safe defaults |
| `shelter/local_settings.py` | ❌ No | Secrets, credentials, DB config, debug flag, all environment-specific values |

### How paths are resolved (no hardcoding)

```python
# settings.py
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# → /home/user/Shelter/app    (local)
# → /srv/Shelter/app          (server)

PARENT_DIR = os.path.dirname(BASE_DIR)
# → /home/user/Shelter        (local)
# → /srv/Shelter              (server)

MEDIA_ROOT          = os.path.join(PARENT_DIR, 'media/')
STATIC_ROOT         = os.path.join(PARENT_DIR, 'static_collected/')
```

This means you can place the `Shelter/` folder anywhere on any machine and the paths resolve correctly — no editing of settings.py required.

### How environment detection works in decorators

`utils_permission.py` uses `BASE_APP_URL` from `local_settings.py` to determine the environment:

```python
def _is_production():
    base_url = getattr(settings, 'BASE_APP_URL', '')
    return '127.0.0.1' not in base_url and 'localhost' not in base_url
```

- Local dev → `BASE_APP_URL = "http://127.0.0.1:8000"` → referer check skipped
- Production → `BASE_APP_URL = "https://shelter-associates.org"` → referer check enforced

---

## Key Configuration Reference

### Installed apps

All of the following must be installed and in `INSTALLED_APPS`:

`django_extensions`, `admin_view_permission`, `django.contrib.gis`, `master`, `component`, `sponsor`, `colorfield`, `mastersheet`, `graphs`, `helpers`, `reports`, `rest_framework`, `rest_auth`, `drf_dynamic_fields`, `widget_tweaks`

### BIRT Report path

The `BIRT_REPORT_CMD` in `local_settings.py` must point to the actual `.rptdesign` file. On the server this is:

```
/srv/Shelter/app/reports/FFReport.rptdesign
```

Update the path in your local `local_settings.py` to match your local reports folder.

### PostGIS version

Set in `settings.py` to match your installed PostGIS:

```python
POSTGIS_VERSION = (2, 0, 3)
```

Check your version with: `psql -c "SELECT PostGIS_version();"`

---

## Git Workflow

### Branch naming

```
feature/short-description     ← new features
fix/short-description         ← bug fixes
refactor/short-description    ← refactoring
```

### Creating a branch and making changes

```bash
cd ~/Shelter/app

# Check current branch
git branch

# Create and switch to a new branch
git checkout -b feature/your-feature-name

# Make your changes, then stage and commit
git add shelter/settings.py
git commit -m "describe what changed and why"

# Push to remote
git push origin feature/your-feature-name
```

### Merging back to main

```bash
git checkout main
git merge feature/your-feature-name
git push origin main
```

### What to never commit

```
shelter/local_settings.py     ← credentials and secrets
media/                        ← user uploaded files
static_collected/             ← generated by collectstatic
*.pyc / __pycache__/          ← compiled Python
```

---

## Troubleshooting

### App won't start — "ImportError: No module named shelter.local_settings"

`local_settings.py` does not exist. Create it from the example template:

```bash
cp shelter/local_settings.example.py shelter/local_settings.py
# Then fill in all CHANGE_ME values
```

If you don't have the credentials, contact the system administrator.

---

### "django.db.utils.OperationalError: FATAL: database does not exist"

The database named in `local_settings.py` hasn't been created yet. Create it:

```bash
sudo -u postgres createdb your_db_name
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE your_db_name TO shelter;"
```

---

### "could not find GEOS library" or GeoDjango import errors

GeoDjango requires native system libraries. Install them:

```bash
sudo apt install libgeos-dev libgdal-dev libproj-dev
```

Then check that Django can find them:

```bash
python -c "from django.contrib.gis.geos import GEOSGeometry; print('GEOS OK')"
```

---

### Static files not loading in production

Run `collectstatic` and make sure Nginx is configured to serve from `STATIC_ROOT`:

```bash
python manage.py collectstatic --noinput
```

Nginx config should include:

```nginx
location /static/ {
    alias /srv/Shelter/static_collected/;
}
location /media/ {
    alias /srv/Shelter/media/;
}
```

---

### request.is_ajax() AttributeError

`is_ajax()` was removed in Django 3.1. The codebase already handles this in `utils_permission.py` by reading `request.headers.get('X-Requested-With')` directly. If you see this error in a view not using that decorator, replace:

```python
# Old — broken on Django 3.1+
if request.is_ajax():

# New — correct
if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
```

---

### Media files not found after moving the codebase

Check that `PARENT_DIR` resolves correctly and the `media/` folder exists beside (not inside) the code:

```bash
python -c "import os; BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath('shelter/settings.py'))); print(os.path.dirname(BASE_DIR))"
ls ~/Shelter/media      # should list uploaded files
```

---

*For setup assistance or missing credentials, contact the system administrator.*