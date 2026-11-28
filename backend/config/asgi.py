"""ASGI entry point: HTTP goes to Django, WebSockets to Channels.

WebSockets pass AllowedHostsOriginValidator (the Origin header must match ALLOWED_HOSTS,
which blocks other websites from opening a socket with the visitor's cookies) and
AuthMiddlewareStack (the session cookie sets scope["user"] and scope["session"]).
Each consumer still checks that the user may see what they ask for."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

# Django must be set up before anything imports models.
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

from config.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
