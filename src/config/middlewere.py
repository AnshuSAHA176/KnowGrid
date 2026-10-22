class RequestLoggerMiddleware:
    def __init__(self, get_responce):
        self.get_responce = get_responce

    def __call__(self, request):
        if "/challenges/" in request.path:
            print('Incoming request: GET /challenges/')
            
        response = self.get_responce(request)
        return response
