from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from channels.auth import AuthMiddlewareStack

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections

from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


@database_sync_to_async
def get_user(validated_token):
    User = get_user_model()

    try:
        return User.objects.get(
            id=validated_token["user_id"]
        )
    except User.DoesNotExist:
        return AnonymousUser()


class JwtAuthMiddleware(BaseMiddleware):

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        print(">>> JWT MIDDLEWARE ENTERED <<<", flush=True)

        close_old_connections()

        query_string = parse_qs(
            scope["query_string"].decode("utf-8")
        )

        token = query_string.get("token", [None])[0]
        print("WS JWT present:", bool(token), flush=True)
        

        if not token:
            scope["user"] = AnonymousUser()
            print("WS rejected: token missing")
            return await super().__call__(scope, receive, send)

        try:
            validated_token = UntypedToken(token)
        except (InvalidToken, TokenError) as exc:
            scope["user"] = AnonymousUser()
            print("WS rejected: invalid token:", str(exc))
            return await super().__call__(scope, receive, send)

        scope["user"] = await get_user(validated_token)
        print("WS authenticated:", scope["user"].is_authenticated)

        return await super().__call__(
            scope,
            receive,
            send
        )


def JwtAuthMiddlewareStack(inner):
    return JwtAuthMiddleware(
        AuthMiddlewareStack(inner)
    )