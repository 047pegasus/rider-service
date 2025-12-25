from django.urls import include, path

app_name = 'api_v1'

urlpatterns = [
    path("riders/", include("apps.riders.urls")),
    path("analytics/", include("apps.analytics.urls")),
    path("deliveries/", include("apps.deliveries.urls")),
    path("events/", include("apps.events.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("orders/", include("apps.orders.urls")),
    path("tracking/", include("apps.tracking.urls")),
]
