from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.events.services import event_service

from .models import Order
from .serializers import OrderSerializer
from .services import order_service


class OrderViewSet(viewsets.ViewSet):
    def list(self, request):
        orders = Order.objects.all()
        serializer = OrderSerializer(orders, many=True)
        if serializer.is_valid():
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=400)

    def retrieve(self, request, pk=None):
        order = Order.objects.get(pk=pk)
        serializer = OrderSerializer(order)
        if serializer.is_valid():
            return Response(serializer.data)
        elif Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)
        else:
            return Response(serializer.errors, status=400)

    def create(self, request):
        serializer = OrderSerializer(data=request.data)
        if serializer.is_valid():
            order = order_service.create_order(serializer.validated_data)
            return Response(OrderSerializer(order).data, status=201)
        return Response(serializer.errors, status=400)

    @action(detail=True, methods=["get"])
    def track(self, request, pk=None):
        tracking_info = order_service.get_order_tracking_info(pk)
        if not tracking_info:
            return Response({"error": "Tracking information not found"}, status=404)
        return Response(
            {
                "order_number": tracking_info["order_number"],
                "status": tracking_info["status"],
                "rider_name": tracking_info["rider"].name
                if tracking_info["rider"]
                else None,
                "rider_phone": tracking_info["rider"].phone
                if tracking_info["rider"]
                else None,
                "current_location": tracking_info["current_location"],
                "estimated_delivery": tracking_info["estimated_delivery"],
            }
        )

    @action(detail=True, methods=["get"])
    def events(self, request, pk=None):
        events = event_service.get_order_events(pk)
        if not events:
            return Response({"error": "Events not found"}, status=404)
        return Response(
            [
                {
                    "event_type": event.event_type,
                    "timestamp": event.timestamp,
                    "location": {"lat": event.location_lat, "lng": event.location_lng}
                    if event.location_lat and event.location_lng
                    else None,
                    "data": event.event_data,
                }
                for event in events
            ]
        )

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        new_status = request.data.get("status")
        delivery_id = request.data.get("delivery_id")
        rider_id = request.data.get("rider_id")
        if not new_status:
            return Response({"error": "Status not provided"}, status=400)
        if not delivery_id:
            return Response({"error": "Delivery ID not provided"}, status=400)
        if not rider_id:
            return Response({"error": "Rider ID not provided"}, status=400)
        order = order_service.update_order_status(pk, new_status, rider_id, delivery_id)
        return Response(OrderSerializer(order).data)
