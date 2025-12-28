from django.urls import re_path

from .consumers import RiderConsumer

websocket_urlpatterns = [
    re_path(r"ws/riders/(?P<ride_id>\w+)/$", RiderConsumer.as_asgi()),
]
