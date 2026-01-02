import json
from typing import Any, Dict, Optional, List, Tuple
from geopy.distance import geodesic
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from infrastructure.cache import redis_client
from apps.riders.models import Rider
from apps.riders.services import rider_service
from apps.orders.models import Order
from apps.events.services import event_service
from apps.events.constants import EventTypes
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import math
from .models import Delivery, DeadLetterQueue


class DeliveryService:
    # Delivery Satus Cache
    def set_delivery_status(
        self, delivery_id: str, status_data: Dict[str, Any], ttl: int = 3600
    ):
        key = f"delivery:status:{delivery_id}"
        redis_client.setex(key, ttl, json.dumps(status_data))

    def get_delivery_status(self, delivery_id: str) -> Optional[Dict[str, Any]]:
        key = f"delivery:status:{delivery_id}"
        data = redis_client.get(key)
        if data:
            return json.loads(str(data))
        return None

    @staticmethod
    def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate distance between two points using geodesic distance (more accurate than Haversine).
        Returns distance in kilometers.
        """
        point1 = (lat1, lng1)
        point2 = (lat2, lng2)
        return geodesic(point1, point2).kilometers

    @staticmethod
    def calculate_route_distance(points: List[Tuple[float, float]]) -> float:
        """
        Calculate total distance for a route with multiple points.
        Points should be a list of (lat, lng) tuples.
        """
        if len(points) < 2:
            return 0.0
        
        total_distance = 0.0
        for i in range(len(points) - 1):
            total_distance += DeliveryService.calculate_distance(
                points[i][0], points[i][1],
                points[i + 1][0], points[i + 1][1]
            )
        return total_distance

    @staticmethod
    def find_nearest_available_rider(
        pickup_lat: float, pickup_lng: float, exclude_rider_id: str = None
    ):
        """
        Find the nearest available rider to a pickup location.
        Riders start at random nearby locations (within 5km radius).
        """
        import random
        import math
        
        available_riders = Rider.objects.filter(
            is_active=True, current_status="available"
        )
        if exclude_rider_id:
            available_riders = available_riders.exclude(id=exclude_rider_id)
        
        if not available_riders:
            return None, None
        
        nearest_rider = None
        min_distance = float('inf')

        for rider in available_riders:
            location = rider_service.get_rider_location(str(rider.id))
            
            # If rider doesn't have a location, assign a random nearby location
            if not location:
                # Generate random location within 5km radius of pickup
                # Using polar coordinates for uniform distribution
                radius_km = random.uniform(1, 5)  # 1-5 km away
                angle = random.uniform(0, 2 * math.pi)
                
                # Convert to lat/lng offset (approximate)
                lat_offset = (radius_km / 111.0) * math.cos(angle)
                lng_offset = (radius_km / (111.0 * math.cos(math.radians(pickup_lat)))) * math.sin(angle)
                
                location = {
                    'lat': pickup_lat + lat_offset,
                    'lng': pickup_lng + lng_offset
                }
                # Set this as the rider's location
                rider_service.set_rider_location(
                    str(rider.id),
                    location,
                    ttl=300
                )

            distance = DeliveryService.calculate_distance(
                pickup_lat, pickup_lng, location['lat'], location['lng']
            )
            if distance < min_distance:
                min_distance = distance
                nearest_rider = rider

        return (nearest_rider, min_distance) if nearest_rider else (None, None)

    @staticmethod
    def find_best_rider_for_batch(orders: List[Order]) -> Tuple[Rider, List[Order], float]:
        """
        Find the best rider for a batch of orders using nearest neighbor algorithm.
        Returns (rider, optimized_order_sequence, total_distance)
        """
        if not orders:
            return None, [], 0.0
        
        # Group orders by proximity to find potential batch assignments
        # For simplicity, we'll find the rider closest to the first order's pickup
        # and optimize the delivery sequence
        
        first_order = orders[0]
        rider, distance = DeliveryService.find_nearest_available_rider(
            float(first_order.pickup_lat), float(first_order.pickup_lng)
        )
        
        if not rider:
            return None, [], 0.0
        
        # Optimize delivery sequence using nearest neighbor
        optimized_sequence = DeliveryService.optimize_delivery_sequence(orders)
        
        # Calculate total route distance
        route_points = []
        rider_location = rider_service.get_rider_location(str(rider.id))
        if rider_location:
            route_points.append((rider_location['lat'], rider_location['lng']))
        
        for order in optimized_sequence:
            route_points.append((float(order.pickup_lat), float(order.pickup_lng)))
            route_points.append((float(order.delivery_lat), float(order.delivery_lng)))
        
        total_distance = DeliveryService.calculate_route_distance(route_points)
        
        return rider, optimized_sequence, total_distance

    @staticmethod
    def optimize_delivery_sequence(orders: List[Order]) -> List[Order]:
        """
        Optimize delivery sequence using nearest neighbor algorithm.
        Returns orders in optimal sequence.
        """
        if len(orders) <= 1:
            return orders
        
        # Start with first order
        sequence = [orders[0]]
        remaining = orders[1:]
        
        current_point = (float(orders[0].delivery_lat), float(orders[0].delivery_lng))
        
        while remaining:
            nearest_order = None
            min_distance = float('inf')
            
            for order in remaining:
                # Calculate distance from current delivery point to next pickup
                distance = DeliveryService.calculate_distance(
                    current_point[0], current_point[1],
                    float(order.pickup_lat), float(order.pickup_lng)
                )
                if distance < min_distance:
                    min_distance = distance
                    nearest_order = order
            
            if nearest_order:
                sequence.append(nearest_order)
                remaining.remove(nearest_order)
                current_point = (float(nearest_order.delivery_lat), float(nearest_order.delivery_lng))
            else:
                break
        
        return sequence

    @staticmethod
    def send_websocket_notification(group_name: str, message_type: str, data: dict):
        """Send WebSocket notification to a channel group"""
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": message_type,
                    "data": data
                }
            )

    @staticmethod
    def assign_delivery(order_id, retry_count=0):
        """
        Assign a delivery to the nearest available rider.
        Accepts orders with status 'pending' or 'ready'.
        """
        try:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(id=order_id)
                
                # Accept both 'pending' and 'ready' status orders
                if order.status not in ['pending', 'ready']:
                    raise ValueError(f'Order is not in a valid state for assignment. Current status: {order.status}')
                
                # Check if delivery already exists
                if Delivery.objects.filter(order=order).exclude(status__in=['failed', 'completed']).exists():
                    existing_delivery = Delivery.objects.filter(order=order).exclude(status__in=['failed', 'completed']).first()
                    if existing_delivery.status == 'assigned':
                        return existing_delivery  # Already assigned
                
                rider, distance = DeliveryService.find_nearest_available_rider(
                    float(order.pickup_lat), float(order.pickup_lng)
                )
                if not rider:
                    # Update retry count and timestamp
                    order.assignment_retry_count = retry_count + 1
                    order.last_assignment_retry_at = timezone.now()
                    order.save()
                    raise Exception('No available riders found !!')

                delivery = Delivery.objects.create(
                    order=order,
                    rider=rider,
                    status='assigned',
                    distance=distance
                )

                rider.current_status = 'busy'
                rider.save()

                # Reset retry count on successful assignment
                order.assignment_retry_count = 0
                order.last_assignment_retry_at = None
                
                # Order status remains 'preparing' or 'ready' until rider accepts
                # Only change if order is still pending
                if order.status == 'pending':
                    order.status = 'preparing'
                order.save()

                rider_service.add_active_delivery(str(rider.id), str(delivery.id))
                
                event_data = {
                    'rider_name': rider.name,
                    'rider_phone': rider.phone,
                    'distance': float(distance) if distance else None
                }
                
                event_service.create_event(
                    delivery_id=delivery.id,
                    order_id = order.id,
                    rider_id = rider.id,
                    event_type= EventTypes.RIDER_ASSIGNED,
                    event_data=event_data
                )
                
                # Send WebSocket notification
                DeliveryService.send_websocket_notification(
                    f"order_{order.id}",
                    "rider_assigned",
                    {
                        "delivery_id": str(delivery.id),
                        "rider": {
                            "id": str(rider.id),
                            "name": rider.name,
                            "phone": rider.phone
                        },
                        "distance": float(distance) if distance else None
                    }
                )
                
                # Also notify rider channel
                DeliveryService.send_websocket_notification(
                    f"rider_{rider.id}",
                    "delivery_assigned",
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
                
                return delivery
        except Exception as e:
            raise e

    @staticmethod
    def retry_unassigned_orders(max_retries=10, max_age_hours=24):
        """
        Retry assignment for orders that are ready but haven't been assigned.
        Uses exponential backoff for retry timing.
        """
        from django.utils import timezone
        from datetime import timedelta
        
        # Find orders that are ready but not assigned
        ready_orders = Order.objects.filter(
            status='ready'
        ).exclude(
            id__in=Delivery.objects.exclude(status__in=['failed', 'completed']).values_list('order_id', flat=True)
        )
        
        retried_count = 0
        assigned_count = 0
        
        for order in ready_orders:
            # Check if order is too old (more than max_age_hours)
            age = timezone.now() - order.created_at
            if age > timedelta(hours=max_age_hours):
                # Mark as cancelled if too old
                order.status = 'cancelled'
                order.save()
                continue
            
            # Calculate exponential backoff: 2^retry_count minutes
            retry_count = order.assignment_retry_count
            if retry_count >= max_retries:
                # Max retries reached, skip
                continue
            
            # Check if enough time has passed since last retry
            if order.last_assignment_retry_at:
                backoff_minutes = min(2 ** retry_count, 60)  # Cap at 60 minutes
                next_retry_time = order.last_assignment_retry_at + timedelta(minutes=backoff_minutes)
                if timezone.now() < next_retry_time:
                    continue  # Not time to retry yet
            
            # Attempt assignment
            try:
                DeliveryService.assign_delivery(str(order.id), retry_count=retry_count)
                assigned_count += 1
                retried_count += 1
            except Exception as e:
                retried_count += 1
                print(f"Retry assignment failed for order {order.id}: {e}")
        
        return {
            'retried': retried_count,
            'assigned': assigned_count
        }

    @staticmethod
    def update_delivery_status(delivery_id, new_status, location=None, route_index=None, simulation_status=None):
        try:
            with transaction.atomic():
                delivery = Delivery.objects.select_for_update().get(id=delivery_id)
                old_status = delivery.status
                delivery.status = new_status
                
                # Persist location if provided
                if location:
                    delivery.last_location_lat = location.get('lat')
                    delivery.last_location_lng = location.get('lng')
                    # Also update rider location in database
                    rider_service.update_rider_location(
                        str(delivery.rider.id),
                        location,
                        delivery_id=str(delivery_id)
                    )
                
                # Persist simulation state if provided
                if route_index is not None:
                    delivery.current_route_index = route_index
                if simulation_status:
                    delivery.simulation_status = simulation_status

                # Update order status based on delivery status
                order = delivery.order
                if new_status == 'accepted':
                    # When rider accepts, order moves to 'assigned' status (rider is on the way to pickup)
                    if order.status in ['preparing', 'ready']:
                        order.status = 'assigned'
                        order.save()
                elif new_status == 'collected':
                    order.status = 'picked_up'
                    order.save()
                elif new_status == 'in_progress':
                    order.status = 'in_transit'
                    order.save()
                elif new_status == 'completed':
                    order.status = 'delivered'
                    order.actual_delivery_time = timezone.now()
                    order.save()
                    delivery.completed_at = timezone.now()
                    rider_service.remove_active_delivery(str(delivery.rider.id), str(delivery.id))
                    delivery.rider.current_status = 'available'
                    delivery.rider.save()
                elif new_status == 'failed':
                    order.status = 'cancelled'
                    order.save()

                delivery.save()
                event_type = EventTypes.ORDER_PICKED_UP if new_status == 'in_progress' else \
                EventTypes.ORDER_DELIVERED if new_status == 'completed' else \
                EventTypes.ORDER_CANCELLED if new_status == 'failed' else None

                if event_type:
                    event_service.create_event(
                        delivery_id = delivery.id,
                        order_id = delivery.order_id,
                        rider_id = delivery.rider_id,
                        event_type = event_type,
                        event_data={
                            'old_status': old_status,
                            'new_status': new_status
                        },
                        location = location
                    )
                
                # Send WebSocket notification with order status update
                DeliveryService.send_websocket_notification(
                    f"order_{delivery.order.id}",
                    "order_update",
                    {
                        "delivery_id": str(delivery.id),
                        "delivery_status": new_status,
                        "order_status": order.status,
                        "old_status": old_status,
                        "location": location,
                        "timestamp": timezone.now().isoformat()
                    }
                )
                
                return delivery

        except Exception as e:
            raise e

delivery_service = DeliveryService()
