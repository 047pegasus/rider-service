"""
ASGI config for rider project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_asgi_app = get_asgi_application()

from apps.orders.routing import websocket_urlpatterns as order_websocket_urlpatterns
from apps.riders.routing import websocket_urlpatterns as rider_websocket_urlpatterns

ws_urlpatterns = [
    *order_websocket_urlpatterns,
    *rider_websocket_urlpatterns,
]

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(ws_urlpatterns))
        ),
    }
)
