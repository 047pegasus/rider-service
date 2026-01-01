from django.urls import include, path
from rest_framework.routers import DefaultRouter

# from .views import (
#     DeliveryEventViewSet,
# )

app_name = "events"

# Router for viewsets
router = DefaultRouter()
# router.register(r"", DeliveryEventViewSet, basename="events")

urlpatterns = [
    # ViewSet routes
    # path("", include(router.urls)),
    # Custom endpoints
]
