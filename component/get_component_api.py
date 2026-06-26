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


def get_request_hash(request, slum_id):
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

    params_string = json.dumps(params, sort_keys=True)
    return hashlib.sha256(params_string.encode("utf-8")).hexdigest()


def compute_and_update_cache(request, slum_id, req_hash):
    """
    Compute fresh response by calling original view
    """
    close_old_connections()
    started_at = pytime.perf_counter()
    started_queries = len(connection.queries)
    try:
        # Call the original view to get JsonResponse
        response = views.get_component(request, slum_id)

        # Convert JsonResponse to dict for storing
        if hasattr(response, "data"):  # If DRF Response
            data = response.data
        else:  # If JsonResponse
            data = json.loads(response.content)

        # Update or create cache
        APICache.objects.update_or_create(
            request_hash=req_hash,
            defaults={"response": data, "expires_at": timezone.now() + TTL},
        )
    finally:
        _log_cache_timing(
            "background_refresh", started_at, started_queries, slum_id=slum_id
        )
        close_old_connections()


def get_component_api(request, slum_id):
    """
    Wrapper view with stale-while-revalidate caching
    """
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
        response = views.get_component(request, slum_id)
        if hasattr(response, "data"):
            data = response.data
        else:
            data = json.loads(response.content)

        APICache.objects.create(
            request_hash=req_hash, response=data, expires_at=timezone.now() + TTL
        )
        _log_cache_timing(
            "cache_miss_compute", started_at, started_queries, slum_id=slum_id
        )
        return JsonResponse(data)
