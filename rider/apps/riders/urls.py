from django.urls import include, path
from rest_framework.routers import DefaultRouter

# from .views import (
#     RiderLocationViewSet,
#     RiderViewSet,
# )

app_name = "riders"

# Router for viewsets
router = DefaultRouter()
# router.register(r"", RiderViewSet, basename="rider")
# router.register(r"locations", RiderLocationViewSet, basename="rider-location")

urlpatterns = [
    # ViewSet routes
    path("", include(router.urls)),
    # Custom endpoints
]
