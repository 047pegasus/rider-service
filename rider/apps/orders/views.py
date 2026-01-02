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
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            order = Order.objects.get(pk=pk)
            serializer = OrderSerializer(order)
            return Response(serializer.data)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

    def create(self, request):
        serializer = OrderSerializer(data=request.data)
        if serializer.is_valid():
            order = order_service.create_order(serializer.validated_data)
            return Response(OrderSerializer(order).data, status=201)
        return Response(serializer.errors, status=400)

    @action(detail=True, methods=["get"])
    def track(self, request, pk=None):
        # Try to get order by UUID first, then by order_number
        try:
            import uuid
            # Check if pk is a valid UUID
            uuid.UUID(pk)
            order = Order.objects.get(id=pk)
        except (ValueError, Order.DoesNotExist):
            # If not a UUID or not found, try order_number
            try:
                order = Order.objects.get(order_number=pk)
            except Order.DoesNotExist:
                return Response({"error": "Order not found"}, status=404)
        
        tracking_info = order_service.get_order_tracking_info(str(order.id))
        if not tracking_info:
            return Response({"error": "Tracking information not found"}, status=404)
        
        order_obj = tracking_info.get("order")
        rider = tracking_info.get("rider")
        
        response_data = {
            "order_id": str(order_obj.id) if order_obj else None,
            "order_number": order_obj.order_number if order_obj else tracking_info.get("order_number"),
            "status": order_obj.status if order_obj else tracking_info.get("status"),
            "pickup_address": order_obj.pickup_address if order_obj else None,
            "pickup_lat": float(order_obj.pickup_lat) if order_obj and order_obj.pickup_lat else None,
            "pickup_lng": float(order_obj.pickup_lng) if order_obj and order_obj.pickup_lng else None,
            "delivery_address": order_obj.delivery_address if order_obj else None,
            "delivery_lat": float(order_obj.delivery_lat) if order_obj and order_obj.delivery_lat else None,
            "delivery_lng": float(order_obj.delivery_lng) if order_obj and order_obj.delivery_lng else None,
            "current_location": tracking_info.get("current_location"),
            "estimated_delivery": tracking_info.get("estimated_delivery").isoformat() if tracking_info.get("estimated_delivery") else None,
        }
        
        if rider:
            response_data["rider"] = {
                "id": str(rider.id),
                "name": rider.name,
                "phone": rider.phone,
            }
        else:
            response_data["rider"] = None
        
        return Response(response_data)

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

    @action(detail=True, methods=["put"])
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

    @action(detail=True, methods=["post"])
    def complete_payment(self, request, pk=None):
        """Mark order payment as completed"""
        try:
            order = Order.objects.get(pk=pk)
            if order.status != 'delivered':
                return Response(
                    {"detail": "Order must be delivered before payment can be completed"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            order.payment_completed = True
            order.save()
            
            return Response(
                {
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                    "payment_completed": True
                },
                status=status.HTTP_200_OK
            )
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
