
import time
import uuid


class APITrackingMiddleware:
    def __init__(self, get_response):
        self.get_response=get_response

    def __call__(self, request):
        try:
            request_id=str(uuid.uuid4())
            request.request_id=request_id
            

            start_time= time.perf_counter()

        
            response=self.get_response(request)
            elapsed_time = (time.perf_counter() - start_time) * 1000
            response['X-Request-ID']=request.request_id

            response["X-Response-Time"] = f"{elapsed_time:.2f}ms"
            
            if response.status_code >=400:
                print(f'ID:-{request.request_id}, method:-{request.method} , path:- {request.path}, status:- {response.status_code }and duration:- {elapsed_time}')
    

       

            return response
        except Exception as exe:
            print(type(exe).__name__)
            print(request.path)
            raise
