"""HTTP client for the AVNI server.

One cached Cognito token shared by every caller in the process, a timeout on
every request, one retry on 401, a shared throttle so parallel workers back
off together, and helpers for AVNI's page-numbered list endpoints.
"""

import base64
import json
import logging
import subprocess
import threading
import time

import requests
from django.conf import settings
from urllib.parse import quote

logger = logging.getLogger(__name__)

TOKEN_REFRESH_MARGIN_SECONDS = 60
TOKEN_FALLBACK_LIFETIME_SECONDS = 3300
COGNITO_DETAILS_TIMEOUT_SECONDS = 30
TOKEN_SUBPROCESS_TIMEOUT_SECONDS = 60
TOKEN_SCRIPT = "avni/data/token.js"


class AvniError(Exception):
    """A non-2xx answer from AVNI."""

    def __init__(self, status_code, url, text=""):
        self.status_code = status_code
        self.url = url
        self.text = text
        super(AvniError, self).__init__(
            "AVNI returned {} for {}: {}".format(status_code, url, text[:300])
        )


def jwt_expiry(token):
    """The `exp` claim of a JWT, or None when it cannot be read."""
    try:
        payload = token.split(".")[1]
        padded = payload + "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(padded)).get("exp")
    except Exception:
        return None


class CognitoTokenSource(object):
    """Logs in to AVNI's Cognito pool through the bundled node script."""

    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.username = username
        self.password = password

    def fetch(self):
        details = requests.get(
            self.base_url + "cognito-details", timeout=COGNITO_DETAILS_TIMEOUT_SECONDS
        ).json()
        command = [
            "node", TOKEN_SCRIPT, details["poolId"], details["clientId"],
            self.username, self.password,
        ]
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=TOKEN_SUBPROCESS_TIMEOUT_SECONDS,
        )
        lines = [line.strip() for line in result.stdout.decode("utf-8").splitlines() if line.strip()]
        if not lines or lines[-1].startswith("Check Credentials"):
            raise AvniError(401, self.base_url + "cognito-details", "Cognito login failed")
        return lines[-1]


class Throttle(object):
    """Pause every caller for a while after each batch of requests."""

    def __init__(self, batch_size, pause_seconds, sleep):
        self.batch_size = batch_size
        self.pause_seconds = pause_seconds
        self.sleep = sleep
        self.count = 0
        self.lock = threading.Lock()

    def before_request(self):
        with self.lock:
            self.count += 1
            due = self.batch_size and self.count % self.batch_size == 0
        if due:
            logger.info("%s AVNI requests made, pausing %ss", self.count, self.pause_seconds)
            self.sleep(self.pause_seconds)


class AvniClient(object):
    def __init__(self, base_url=None, token_source=None, transport=None, sleep=time.sleep,
                 timeout=None, batch_size=100, batch_pause_seconds=15):
        self.base_url = base_url or settings.AVNI_URL
        self.token_source = token_source or CognitoTokenSource(
            self.base_url, settings.AVNI_USERNAME, settings.AVNI_PASSWORD
        )
        self.transport = transport or requests.request
        self.timeout = timeout or getattr(settings, "AVNI_REQUEST_TIMEOUT", 60)
        self.throttle = Throttle(batch_size, batch_pause_seconds, sleep)
        self.cached_token = None
        self.token_expires_at = 0
        self.token_lock = threading.Lock()

    # -- token -------------------------------------------------------------

    def token(self):
        with self.token_lock:
            if self.token_is_fresh():
                return self.cached_token
            return self.refresh_token_locked()

    def refresh_token(self):
        with self.token_lock:
            return self.refresh_token_locked()

    def token_is_fresh(self):
        return bool(self.cached_token) and time.time() < self.token_expires_at - TOKEN_REFRESH_MARGIN_SECONDS

    def refresh_token_locked(self):
        self.cached_token = self.token_source.fetch()
        self.token_expires_at = jwt_expiry(self.cached_token) or (
            time.time() + TOKEN_FALLBACK_LIFETIME_SECONDS
        )
        return self.cached_token

    # -- requests ----------------------------------------------------------

    def request(self, method, path, body=None, timeout=None):
        url = self.base_url + path
        response = self.send(method, url, body, timeout, self.token())
        if response.status_code == 401:
            response = self.send(method, url, body, timeout, self.refresh_token())
        return response

    def send(self, method, url, body, timeout, token):
        self.throttle.before_request()
        headers = {"auth-token": token, "accept": "application/json"}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body)
        return self.transport(method, url, headers=headers, data=data, timeout=timeout or self.timeout)

    def get(self, path, timeout=None):
        return self.request("GET", path, timeout=timeout)

    def put(self, path, body, timeout=None):
        return self.request("PUT", path, body=body, timeout=timeout)

    def patch(self, path, body, timeout=None):
        return self.request("PATCH", path, body=body, timeout=timeout)

    def get_json(self, path, timeout=None):
        response = self.get(path, timeout=timeout)
        if response.status_code != 200:
            raise AvniError(response.status_code, self.base_url + path, response.text)
        return response.json()

    # -- list endpoints ----------------------------------------------------

    def iter_pages(self, path, timeout=None):
        """Yield the `content` list of every page of a list endpoint."""
        first = self.get_json(path, timeout=timeout)
        yield first.get("content", [])
        for page in range(1, first.get("totalPages", 0)):
            yield self.get_json(page_path(path, page), timeout=timeout).get("content", [])

    def count(self, path, timeout=None):
        """Exact record count; AVNI's totalElements is only the page size."""
        first = self.get_json(path, timeout=timeout)
        pages = first.get("totalPages", 0)
        page_size = first.get("pageSize") or len(first.get("content", []))
        if pages <= 1:
            return {"total": len(first.get("content", [])), "pages": pages, "page_size": page_size}
        last = self.get_json(page_path(path, pages - 1), timeout=timeout)
        total = (pages - 1) * page_size + len(last.get("content", []))
        return {"total": total, "pages": pages, "page_size": page_size}

    # -- media -------------------------------------------------------------

    def signed_media_url(self, raw_url, timeout=10):
        response = self.get("media/signedUrl?url=" + quote(raw_url, safe=""), timeout=timeout)
        if response.status_code != 200:
            raise AvniError(response.status_code, raw_url, response.text)
        return response.text.strip().strip('"')


def page_path(path, page):
    joiner = "&" if "?" in path else "?"
    return "{}{}page={}".format(path, joiner, page)


shared_client = None
shared_client_lock = threading.Lock()


def client():
    """The process-wide client, so every caller shares one token and throttle."""
    global shared_client
    with shared_client_lock:
        if shared_client is None:
            shared_client = AvniClient()
        return shared_client


def use_client(instance):
    """Make `client()` return this instance (tests inject a fake here)."""
    global shared_client
    with shared_client_lock:
        shared_client = instance


def reset_client():
    use_client(None)
