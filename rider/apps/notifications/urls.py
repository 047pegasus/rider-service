from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    NotificationViewSet,
)

app_name = "notifications"

# Router for viewsets
router = DefaultRouter()
router.register(r"", NotificationViewSet, basename="notifications")

urlpatterns = [
    # ViewSet routes
    path("", include(router.urls)),
    # Custom endpoints
]
