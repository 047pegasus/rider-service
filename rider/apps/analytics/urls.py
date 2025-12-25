from django.urls import include, path
from rest_framework.routers import DefaultRouter

# from .views import (
#     AnalyticsViewSet,
# )

app_name = "analytics"

# Router for viewsets
router = DefaultRouter()
# router.register(r"", AnalyticsViewSet, basename="analytics")

urlpatterns = [
    # ViewSet routes
    path("", include(router.urls)),
    # Custom endpoints
]
