from . import views
from graphs.models import APICache
from django.http import HttpResponse, JsonResponse
from django.db import IntegrityError, connection, close_old_connections, transaction
from django.utils import timezone
from datetime import timedelta
import threading
import json
import hashlib
import time as pytime

TTL = timedelta(hours=1)  # Cache expiration time


def _log_cache_timing(stage, started_at, started_queries, **details):
    elapsed_ms = (pytime.perf_counter() - started_at) * 1000.0
    query_delta = len(connection.queries) - started_queries
    extra = ""
    if details:
        extra = " | " + ", ".join(
            "{}={}".format(key, value) for key, value in details.items()
        )
    message = "Component cache timing [{}]: {:.1f} ms, queries=+{}{}".format(
        stage, elapsed_ms, query_delta, extra
    )


def _read_cache(req_hash):
    """Return (response_text, expires_at) for a cache row, or None.

    Reads the column directly rather than through the ORM: `response` is a
    jsonfield, so loading it via the model would json.loads the whole payload
    only for us to json.dumps it straight back out. On the largest slum that
    round trip costs ~750 ms per request. The column is plain text, so the
    stored JSON can be streamed to the client untouched.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT response, expires_at FROM graphs_apicache WHERE request_hash = %s",
            [req_hash],
        )
        return cursor.fetchone()


def _write_cache(req_hash, payload_text, expires_at):
    """Upsert a cache row from already-serialised JSON text.

    Bypasses the ORM for the same reason as _read_cache, and additionally stores
    compact JSON: jsonfield is configured with indent=4, which inflates the
    largest payload from 10.2 MB to 44.1 MB of mostly spaces. `created_at` is
    supplied explicitly because auto_now_add is applied in Python, not the DB.

    UPDATE-then-INSERT rather than INSERT ... ON CONFLICT, which needs
    PostgreSQL 9.5+; production runs older than that. Two requests missing the
    same key concurrently can both reach the INSERT, so the unique violation is
    caught and retried as an UPDATE. The retry runs in its own atomic block
    because a failed statement aborts the surrounding transaction.
    """
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE graphs_apicache SET response = %s, expires_at = %s "
                "WHERE request_hash = %s",
                [payload_text, expires_at, req_hash],
            )
            if cursor.rowcount:
                return

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO graphs_apicache "
                    "(request_hash, response, created_at, expires_at) "
                    "VALUES (%s, %s, %s, %s)",
                    [req_hash, payload_text, timezone.now(), expires_at],
                )
    except IntegrityError:
        # Another request inserted this key between our UPDATE and INSERT.
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE graphs_apicache SET response = %s, expires_at = %s "
                    "WHERE request_hash = %s",
                    [payload_text, expires_at, req_hash],
                )


def _payload_text(response):
    """Serialised JSON for a view's response, without a needless re-encode."""
    if hasattr(response, "content"):
        return response.content.decode("utf-8")
    return json.dumps(response.data, separators=(",", ":"))


def _json_response(payload_text):
    return HttpResponse(payload_text, content_type="application/json")


def _is_expired(expires_at):
    return expires_at is not None and timezone.now() > expires_at


def get_request_hash(request, slum_id, endpoint=None):
    """
    Generate cache key based on:
    - slum_id
    - request GET params
    - user identity
        - authenticated → per-user cache
        - anonymous → shared cache
    """

    if request.user.is_authenticated:
        user_key = f"user:{request.user.id}"
    else:
        # ALL anonymous users share the SAME cache
        user_key = "anon"

    params = {"slum_id": slum_id, "user": user_key, **request.GET.dict()}
    if endpoint:
        params["endpoint"] = endpoint

    params_string = json.dumps(params, sort_keys=True)
    return hashlib.sha256(params_string.encode("utf-8")).hexdigest()


def compute_and_update_cache(request, slum_id, req_hash, view=None):
    """
    Compute fresh response by calling original view
    """
    close_old_connections()
    started_at = pytime.perf_counter()
    started_queries = len(connection.queries)
    try:
        response = (view or views.get_component)(request, slum_id)
        _write_cache(req_hash, _payload_text(response), timezone.now() + TTL)
    finally:
        _log_cache_timing(
            "background_refresh", started_at, started_queries, slum_id=slum_id
        )
        close_old_connections()


def _cached_view(request, slum_id, view, endpoint=None):
    """Stale-while-revalidate wrapper shared by the component endpoints.

    Serves the cached bytes immediately, even when stale, and kicks off a
    background recompute when the entry has expired or a refresh was forced.
    """
    started_at = pytime.perf_counter()
    started_queries = len(connection.queries)
    req_hash = get_request_hash(request, slum_id, endpoint=endpoint)
    force_refresh = request.headers.get("Force-Refresh-Flag", "0") == "1"

    row = _read_cache(req_hash)
    if row is not None:
        payload_text, expires_at = row
        _log_cache_timing(
            "cache_lookup_hit",
            started_at,
            started_queries,
            slum_id=slum_id,
            expired=_is_expired(expires_at),
            force_refresh=force_refresh,
        )

        if _is_expired(expires_at) or force_refresh:
            refresh_thread = threading.Thread(
                target=compute_and_update_cache,
                args=(request, slum_id, req_hash, view),
            )
            refresh_thread.daemon = True
            refresh_thread.start()

        return _json_response(payload_text)

    _log_cache_timing("cache_lookup_miss", started_at, started_queries, slum_id=slum_id)

    response = view(request, slum_id)
    payload_text = _payload_text(response)
    _write_cache(req_hash, payload_text, timezone.now() + TTL)
    _log_cache_timing("cache_miss_compute", started_at, started_queries, slum_id=slum_id)
    return _json_response(payload_text)


def get_component_api(request, slum_id):
    """Cached /component/get_component/<slum_id>.

    `?geom=panel` produces a separate, much smaller cache entry automatically,
    because get_request_hash folds request.GET into the key.
    """
    return _cached_view(request, slum_id, views.get_component)


def get_component_geometry_api(request, slum_id):
    """Cached /component/get_component_geometry/<slum_id>.

    Keyed per requested layer set, again via request.GET in the hash.
    """
    return _cached_view(
        request, slum_id, views.get_component_geometry, endpoint="component_geometry"
    )
