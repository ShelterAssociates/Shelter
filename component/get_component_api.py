from . import views
from graphs.models import APICache
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
import threading
import json
import hashlib

TTL = timedelta(hours=1)  # Cache expiration time

def get_request_hash(request, slum_id):
    """
    Generate a unique hash from slum_id and request GET parameters
    """
    params = {"slum_id": slum_id, **request.GET.dict()}
    params_string = json.dumps(params, sort_keys=True)
    return hashlib.sha256(params_string.encode("utf-8")).hexdigest()


def compute_and_update_cache(request, slum_id, req_hash):
    """
    Compute fresh response by calling original view
    """
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
        defaults={
            "response": data,
            "expires_at": timezone.now() + TTL
        }
    )


def get_component_api(request, slum_id):
    """
    Wrapper view with stale-while-revalidate caching
    """
    req_hash = get_request_hash(request, slum_id)
    flag = request.headers.get("Force-Refresh-Flag", "0")

    try:
        cache = APICache.objects.get(request_hash=req_hash)
        #print("Cache hit")
        # If cache is expired, start background refresh
        if cache.is_expired() or flag == "1":
            # Start background refresh
           # print("Cache expired, refreshing in background...")
            threading.Thread(target=compute_and_update_cache, args=(request, slum_id, req_hash)).start()

        # Return cached response immediately (even if stale)
        threading.Thread(target=compute_and_update_cache, args=(request, slum_id, req_hash)).start()
        return JsonResponse(cache.response)

    except APICache.DoesNotExist:
        #print("Cache miss, computing response...")
        # No cache → compute synchronously
        response = views.get_component(request, slum_id)
        if hasattr(response, "data"):
            data = response.data
        else:
            data = json.loads(response.content)

        APICache.objects.create(
            request_hash=req_hash,
            response=data,
            expires_at=timezone.now() + TTL
        )
        return JsonResponse(data)
