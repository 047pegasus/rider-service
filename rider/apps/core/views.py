import redis
from django.core.cache import cache
from django.db import connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """Basic health check endpoint"""

    permission_classes = []

    def get(self, request):
        return Response(
            {
                "status": "healthy" if connection.is_connected() else "unhealthy",
                "service": "delivery-tracking",
            },
            status=status.HTTP_200_OK,
        )


class ReadinessCheckView(APIView):
    """Readiness check - verifies all dependencies"""

    permission_classes = []

    def get(self, request):
        checks = {
            "database": self._check_database(),
            "redis": self._check_redis(),
        }

        all_healthy = all(checks.values())

        return Response(
            {"status": "ready" if all_healthy else "not_ready", "checks": checks},
            status=status.HTTP_200_OK
            if all_healthy
            else status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    def _check_database(self):
        try:
            connection.ensure_connection()
            return True
        except Exception:
            return False

    def _check_redis(self):
        try:
            cache.set("health_check", "ok", 10)
            return cache.get("health_check") == "ok"
        except Exception:
            return False
