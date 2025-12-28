from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BatchDeliveryViewSet, DeliveryViewSet

app_name = "deliveries"

# Router for viewsets
router = DefaultRouter()
router.register(r"", DeliveryViewSet, basename="deliveries")
router.register(r"batch", BatchDeliveryViewSet, basename="batch-deliveries")

urlpatterns = [
    # ViewSet routes
    path("", include(router.urls)),
    # Custom endpoints
]
