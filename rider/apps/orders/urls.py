from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    OrderViewSet,
)

app_name = "orders"

# Router for viewsets
router = DefaultRouter()
router.register(r"", OrderViewSet, basename="order")

urlpatterns = [
    # ViewSet routes
    path("", include(router.urls)),
    # Custom endpoints
]
