import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.asgi import get_asgi_application

# Initialize Django before importing modules that load Django models.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

from .autjwtcustommiddlewere import JwtAuthMiddlewareStack
from apps.coding_challenges.webshocker_urls import websocket_urlpatterns


class WebSocketDebugMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            print(">>> ASGI WEBSOCKET ROUTER REACHED <<<", flush=True)

        return await self.app(scope, receive, send)


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": WebSocketDebugMiddleware(
            JwtAuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
