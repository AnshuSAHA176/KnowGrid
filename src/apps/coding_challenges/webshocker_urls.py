from django.urls import path
from .consumer import SendEventConsumer

websocket_urlpatterns = [
    path(
        "ws/submissions/<uuid:submission_id>/",
        SendEventConsumer.as_asgi(),
    ),
]