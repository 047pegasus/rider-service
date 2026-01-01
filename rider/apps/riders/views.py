from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from rider.apps.riders.services import rider_service

from .models import Rider
from .serializers import RiderSerializer


class RiderViewSet(viewsets.ViewSet):
    def list(self, request):
        riders = Rider.objects.all()
        serializer = RiderSerializer(riders, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            rider = Rider.objects.get(pk=pk)
            serializer = RiderSerializer(rider)
            return Response(serializer.data)
        except Rider.DoesNotExist:
            return Response(
                {"error": "Rider not found"}, status=status.HTTP_404_NOT_FOUND
            )

    def create(self, request):
        serializer = RiderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def update_location(self, request, pk=None):
        try:
            location_data = request.data
            delivery_id = request.data.get("delivery_id")
            if not delivery_id:
                return Response(
                    {"error": "Delivery ID is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            location = rider_service.update_rider_location(
                rider_id=pk, location_data=location_data, delivery_id=delivery_id
            )
            return Response(
                {
                    "message": "Location updated successfully",
                    "timestamp": location.timestamp,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["get"])
    def current_location(self, request, pk=None):
        try:
            location = rider_service.get_rider_location(rider_id=pk)
            if not location:
                return Response(
                    {"error": "Location not available !!"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(location)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["get"])
    def location_history(self, request, pk=None):
        limit = int(request.query_params.get("limit", 10))
        history = rider_service.get_rider_location_history(rider_id=pk, limit=limit)
        if not history:
            return Response(
                {"error": "Location history not available !!"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            [
                {
                    "lat": float(location.lat),
                    "lng": float(location.lng),
                    "timestamp": location.timestamp.isoformat(),
                    "speed": float(location.speed),
                }
                for location in history
            ]
        )
