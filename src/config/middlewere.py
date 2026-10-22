
import time
import uuid
import json
from django.http import HttpResponse


class RequestProtectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if "../" in request.path:
            return HttpResponse(
                json.dumps({"error": "suspicious"}),
                status=400,
                content_type="application/json",
            )

        start_time = time.perf_counter()

        request_id = str(uuid.uuid4())
        request.request_id = request_id

        response = self.get_response(request)
        response["X-Request-ID"] = request_id

        elapsed = time.perf_counter() - start_time

        if elapsed > 1:
            print(
                f"Slow request: {request.method} "
                f"{request.path} took {elapsed:.3f}s"
            )

        return response
