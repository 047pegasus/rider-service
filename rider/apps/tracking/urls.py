from django.urls import include, path
from rest_framework.routers import DefaultRouter

# from .views import TrackingViewSet

app_name = "tracking"

# Router for viewsets
router = DefaultRouter()
# router.register(r"", TrackingViewSet, basename="tracking")

urlpatterns = [
    # ViewSet routes
    path("", include(router.urls)),
    # Custom endpoints
]
