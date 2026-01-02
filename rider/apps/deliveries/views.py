from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Delivery
from .serializers import DeliverySerializer
from .services import delivery_service


class DeliveryViewSet(viewsets.ViewSet):
    def list(self, request):
        deliveries = Delivery.objects.all()
        serializer = DeliverySerializer(deliveries, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            delivery = Delivery.objects.get(pk=pk)
            serializer = DeliverySerializer(delivery)
            return Response(serializer.data)
        except Delivery.DoesNotExist:
            return Response(
                {"detail": "Delivery not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"])
    def assign(self, request):
        order_id = request.data.get("order_id")
        if not order_id:
            return Response(
                {"detail": "Order ID is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            delivery = delivery_service.assign_delivery(order_id)
            return Response(
                DeliverySerializer(delivery).data, status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["put"])
    def update_status(self, request, pk=None):
        try:
            new_status = request.data.get("status")
            location = request.data.get("location")
            route_index = request.data.get("route_index")
            simulation_status = request.data.get("simulation_status")
            
            # If only location/route_index/simulation_status is provided, update without changing status
            if new_status is None:
                # Just update location and simulation state
                from apps.deliveries.models import Delivery
                from django.db import transaction
                from apps.riders.services import rider_service
                
                with transaction.atomic():
                    delivery = Delivery.objects.select_for_update().get(id=pk)
                    
                    if location:
                        delivery.last_location_lat = location.get('lat')
                        delivery.last_location_lng = location.get('lng')
                        # Also update rider location in database
                        rider_service.update_rider_location(
                            str(delivery.rider.id),
                            location,
                            delivery_id=str(delivery.id)
                        )
                    
                    if route_index is not None:
                        delivery.current_route_index = route_index
                    if simulation_status:
                        delivery.simulation_status = simulation_status
                    
                    delivery.save()
                
                return Response(
                    DeliverySerializer(delivery).data, status=status.HTTP_200_OK
                )
            else:
                # Update status and other fields
                delivery = delivery_service.update_delivery_status(
                    pk, new_status, location, route_index, simulation_status
                )
                return Response(
                    DeliverySerializer(delivery).data, status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=["get"])
    def state(self, request, pk=None):
        """Get delivery state including simulation progress for restoration"""
        try:
            delivery = Delivery.objects.get(pk=pk)
            return Response({
                "delivery_id": str(delivery.id),
                "status": delivery.status,
                "simulation_status": delivery.simulation_status,
                "current_route_index": delivery.current_route_index,
                "last_location": {
                    "lat": float(delivery.last_location_lat) if delivery.last_location_lat else None,
                    "lng": float(delivery.last_location_lng) if delivery.last_location_lng else None,
                },
                "order": {
                    "id": str(delivery.order.id),
                    "order_number": delivery.order.order_number,
                    "status": delivery.order.status,
                    "pickup_location": {
                        "lat": float(delivery.order.pickup_lat),
                        "lng": float(delivery.order.pickup_lng),
                        "address": delivery.order.pickup_address
                    },
                    "delivery_location": {
                        "lat": float(delivery.order.delivery_lat),
                        "lng": float(delivery.order.delivery_lng),
                        "address": delivery.order.delivery_address
                    }
                }
            }, status=status.HTTP_200_OK)
        except Delivery.DoesNotExist:
            return Response(
                {"detail": "Delivery not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        """Rider accepts a delivery assignment"""
        try:
            delivery = Delivery.objects.get(pk=pk)
            if delivery.status != 'assigned':
                return Response(
                    {"detail": "Delivery is not in assigned status"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Use update_delivery_status to properly handle status updates and events
            delivery = delivery_service.update_delivery_status(pk, 'accepted')
            
            # Get updated order
            from apps.orders.models import Order
            order = delivery.order
            
            # Send WebSocket notification to order channel
            from apps.deliveries.services import DeliveryService
            DeliveryService.send_websocket_notification(
                f"order_{order.id}",
                "order_update",
                {
                    "delivery_id": str(delivery.id),
                    "delivery_status": "accepted",
                    "order_status": order.status,
                    "rider": {
                        "id": str(delivery.rider.id),
                        "name": delivery.rider.name,
                        "phone": delivery.rider.phone
                    },
                    "timestamp": delivery.updated_at.isoformat()
                }
            )
            
            # Send WebSocket notification to rider channel
            DeliveryService.send_websocket_notification(
                f"rider_{delivery.rider.id}",
                "delivery_accepted",
                {
                    "delivery_id": str(delivery.id),
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                    "pickup_location": {
                        "lat": float(order.pickup_lat),
                        "lng": float(order.pickup_lng),
                        "address": order.pickup_address
                    },
                    "delivery_location": {
                        "lat": float(order.delivery_lat),
                        "lng": float(order.delivery_lng),
                        "address": order.delivery_address
                    }
                }
            )
            
            return Response(
                DeliverySerializer(delivery).data, status=status.HTTP_200_OK
            )
        except Delivery.DoesNotExist:
            return Response(
                {"detail": "Delivery not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def deny(self, request, pk=None):
        """Rider denies a delivery assignment"""
        try:
            delivery = Delivery.objects.get(pk=pk)
            if delivery.status != 'assigned':
                return Response(
                    {"detail": "Delivery is not in assigned status"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            delivery.status = 'denied'
            delivery.save()
            
            # Increment denial count on order
            from apps.orders.models import Order
            order = delivery.order
            order.denial_count += 1
            order.save()
            
            # If 5 denials, cancel the order
            if order.denial_count >= 5:
                order.status = 'cancelled'
                order.save()
                
                # Cancel all pending deliveries for this order
                Delivery.objects.filter(order=order, status='assigned').update(status='failed')
                
                # Send cancellation notification
                from apps.deliveries.services import DeliveryService
                DeliveryService.send_websocket_notification(
                    f"order_{order.id}",
                    "order_cancelled",
                    {
                        "order_id": str(order.id),
                        "order_number": order.order_number,
                        "reason": "Excessive denials (5 denials)"
                    }
                )
            else:
                # Try to assign to another rider
                try:
                    new_delivery = delivery_service.assign_delivery(str(order.id))
                    # Send WebSocket notification about new assignment
                    from apps.deliveries.services import DeliveryService
                    DeliveryService.send_websocket_notification(
                        f"rider_{new_delivery.rider.id}",
                        "delivery_assigned",
                        {
                            "delivery_id": str(new_delivery.id),
                            "order_id": str(order.id),
                            "order_number": order.order_number,
                            "pickup_location": {
                                "lat": float(order.pickup_lat),
                                "lng": float(order.pickup_lng),
                                "address": order.pickup_address
                            },
                            "delivery_location": {
                                "lat": float(order.delivery_lat),
                                "lng": float(order.delivery_lng),
                                "address": order.delivery_address
                            },
                            "denial_count": order.denial_count
                        }
                    )
                except Exception as e:
                    print(f"Failed to reassign delivery after denial: {e}")
            
            return Response(
                {
                    "delivery_id": str(delivery.id),
                    "status": "denied",
                    "denial_count": order.denial_count,
                    "order_cancelled": order.status == 'cancelled'
                },
                status=status.HTTP_200_OK
            )
        except Delivery.DoesNotExist:
            return Response(
                {"detail": "Delivery not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"])
    def assign_batch(self, request):
        """Assign multiple orders to a single rider with optimized route"""
        order_ids = request.data.get("order_ids", [])
        if not order_ids:
            return Response(
                {"detail": "Order IDs are required"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            from apps.orders.models import Order
            orders = Order.objects.filter(id__in=order_ids, status="pending")
            if not orders.exists():
                return Response(
                    {"detail": "No pending orders found"}, status=status.HTTP_400_BAD_REQUEST
                )
            
            rider, optimized_orders, total_distance = delivery_service.find_best_rider_for_batch(
                list(orders)
            )
            
            if not rider:
                return Response(
                    {"detail": "No available riders found"}, status=status.HTTP_404_NOT_FOUND
                )
            
            # Create deliveries for each order
            deliveries = []
            for order in optimized_orders:
                delivery = delivery_service.assign_delivery(str(order.id))
                deliveries.append(delivery)
            
            return Response(
                {
                    "rider_id": str(rider.id),
                    "rider_name": rider.name,
                    "total_distance": total_distance,
                    "deliveries": [DeliverySerializer(d).data for d in deliveries],
                    "optimized_sequence": [str(o.id) for o in optimized_orders]
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
