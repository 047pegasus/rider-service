from django.urls import path
from apps.core.views import HealthCheckView, ReadinessCheckView

app_name = 'core'

urlpatterns = [
    path('', HealthCheckView.as_view(), name='health-check'),
    path('ready/', ReadinessCheckView.as_view(), name='readiness-check'),
]