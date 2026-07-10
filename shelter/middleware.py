import logging
import time

logger = logging.getLogger("request_logger")


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        user = getattr(request, "user", None)
        username = getattr(user, "username", "Anonymous") if user else "Anonymous"

        logger.info(
            "REQUEST: method=%s path=%s user=%s GET=%s POST=%s",
            request.method,
            request.path,
            username,
            dict(request.GET),
            dict(request.POST),
        )

        response = self.get_response(request)

        duration = time.time() - start_time
        logger.info(
            "RESPONSE: method=%s path=%s status=%s duration=%.3fs",
            request.method,
            request.path,
            response.status_code,
            duration,
        )

        return response
