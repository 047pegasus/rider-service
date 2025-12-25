from django.urls import include, path
from rest_framework.routers import DefaultRouter

# from .views import (
#     EventViewSet,
# )

app_name = "events"

# Router for viewsets
router = DefaultRouter()
# router.register(r"", EventViewSet, basename="events")

urlpatterns = [
    # ViewSet routes
    path("", include(router.urls)),
    # Custom endpoints
]
