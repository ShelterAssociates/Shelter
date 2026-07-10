import logging
import time

logger = logging.getLogger("request_logger")


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        logger.info(
            "REQUEST: method=%s path=%s GET=%s POST=%s",
            request.method,
            request.path,
            dict(request.GET),
            dict(request.POST),
        )

        response = self.get_response(request)

        # request.user is only reliably set AFTER get_response runs,
        # since AuthenticationMiddleware executes deeper in the chain.
        user = getattr(request, "user", None)
        username = getattr(user, "username", "Anonymous") if user and user.is_authenticated else "Anonymous"

        duration = time.time() - start_time
        logger.info(
            "RESPONSE: method=%s path=%s status=%s duration=%.3fs user=%s",
            request.method,
            request.path,
            response.status_code,
            duration,
            username,
        )

        return response