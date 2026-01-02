from django.urls import re_path

from .consumers import RiderConsumer

websocket_urlpatterns = [
    re_path(r"ws/riders/(?P<ride_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/$", RiderConsumer.as_asgi()),
]
