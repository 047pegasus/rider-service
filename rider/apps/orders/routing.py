from django.urls import re_path

from .consumers import OrderConsumer

websocket_urlpatterns = [
    re_path(r"^ws/orders/(?P<order_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/$", OrderConsumer.as_asgi()),
]
