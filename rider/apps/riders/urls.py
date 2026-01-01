from django.urls import include, path
from rest_framework.routers import DefaultRouter

# from rest_framework_nested.routers import NestedDefaultRouter
from .views import (
    # RiderLocationsViewSet,
    RiderViewSet,
)

app_name = "riders"

# Router for viewsets
router = DefaultRouter()
router.register(r"", RiderViewSet, basename="rider")

# rider_location_router = NestedDefaultRouter(router, r"rider", lookup="rider")
# router.register(r"locations", RiderLocationsViewSet, basename="rider-location")

urlpatterns = [
    path("", include(router.urls)),
    # path("", include(rider_location_router.urls)),
]
