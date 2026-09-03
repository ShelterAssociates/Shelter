from . import views
from graphs.models import APICache
from django.http import JsonResponse
from django.db import connection, close_old_connections
from django.utils import timezone
from datetime import timedelta
import threading
import json
import hashlib
import time as pytime

# Same stale-while-revalidate approach as get_component_api.py, reusing the
# same APICache model — kept as a separate cache namespace (see the
# "endpoint" key in get_request_hash below) since this is a distinct API
# call from get_component, not a replacement for it.
TTL = timedelta(hours=1)  # Cache expiration time


def _log_cache_timing(stage, started_at, started_queries, **details):
    elapsed_ms = (pytime.perf_counter() - started_at) * 1000.0
    query_delta = len(connection.queries) - started_queries
    extra = ""
    if details:
        extra = " | " + ", ".join(
            "{}={}".format(key, value) for key, value in details.items()
        )
    message = "Ward-wise data cache timing [{}]: {:.1f} ms, queries=+{}{}".format(
        stage, elapsed_ms, query_delta, extra
    )


def get_request_hash(request, slum_id):
    """
    Generate cache key based on:
    - this endpoint (so it can't collide with get_component_api's cache
      entries, which hash the same slum_id/user/GET-params shape)
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

    params = {
        "endpoint": "ward_wise_data",
        "slum_id": slum_id,
        "user": user_key,
        **request.GET.dict(),
    }

    params_string = json.dumps(params, sort_keys=True)
    return hashlib.sha256(params_string.encode("utf-8")).hexdigest()


def compute_and_update_cache(request, slum_id, req_hash):
    """
    Compute fresh response by calling the original view.
    """
    close_old_connections()
    started_at = pytime.perf_counter()
    started_queries = len(connection.queries)
    try:
        response = views.get_ward_wise_data(request)
        data = json.loads(response.content)

        APICache.objects.update_or_create(
            request_hash=req_hash,
            defaults={"response": data, "expires_at": timezone.now() + TTL},
        )
    finally:
        _log_cache_timing(
            "background_refresh", started_at, started_queries, slum_id=slum_id
        )
        close_old_connections()


def get_ward_wise_data_api(request):
    """
    Wrapper view with stale-while-revalidate caching around
    `views.get_ward_wise_data`, mirroring get_component_api.get_component_api.
    """
    slum_id = request.GET.get("slum_id") or request.GET.get("slumId")
    if not slum_id:
        return JsonResponse({"error": "slum_id is required"}, status=400)

    started_at = pytime.perf_counter()
    started_queries = len(connection.queries)
    req_hash = get_request_hash(request, slum_id)
    flag = request.headers.get("Force-Refresh-Flag", "0")

    try:
        cache = APICache.objects.get(request_hash=req_hash)
        _log_cache_timing(
            "cache_lookup_hit",
            started_at,
            started_queries,
            slum_id=slum_id,
            expired=cache.is_expired(),
            force_refresh=flag,
        )

        # If cache is expired, start background refresh
        if cache.is_expired() or flag == "1":
            refresh_thread = threading.Thread(
                target=compute_and_update_cache, args=(request, slum_id, req_hash)
            )
            refresh_thread.daemon = True
            refresh_thread.start()

        # Return cached response immediately (even if stale)
        return JsonResponse(cache.response)

    except APICache.DoesNotExist:
        _log_cache_timing(
            "cache_lookup_miss", started_at, started_queries, slum_id=slum_id
        )

        # No cache → compute synchronously
        response = views.get_ward_wise_data(request)
        data = json.loads(response.content)

        APICache.objects.create(
            request_hash=req_hash, response=data, expires_at=timezone.now() + TTL
        )
        _log_cache_timing(
            "cache_miss_compute", started_at, started_queries, slum_id=slum_id
        )
        return JsonResponse(data)
