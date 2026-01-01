import json
from typing import Any, Dict, Optional
import math
from infrastructure.cache import redis_client
from apps.
from apps.riders.models import Rider
from apps.riders.services import rider_service
from apps.orders.models import Order
from apps.events.services import event_service
from apps.events.constants import EventTypes
from django.db import transaction
from django.utils import timezone
from .models import Delivery


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
        # Haversine formula to calculate distance between two points on Earth
        radius = 6371.0  # Radius of Earth in kilometers
        dlat = (lat2 - lat1) * (math.pi / 180)
        dlon = (lng2 - lng1) * (math.pi / 180)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1 * (math.pi / 180))
            * math.cos(lat2 * (math.pi / 180))
            * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = radius * c
        return distance

    @staticmethod
    def find_nearest_available_rider(
        pickup_lat: float, pickup_lng: float
    ):
        available_riders = Rider.objects.filter(
            is_active=True, current_status="available"
        )
        if not available_riders:
            return None
        nearest_rider = None
        min_distance = float('inf')

        for rider in available_riders:
            location = rider_service.get_rider_location(str(rider.id))
            if not location:
                continue

            distance = DeliveryService.calculate_distance(
                pickup_lat, pickup_lng, location['lat'], location['lng']
            )
            if distance < min_distance:
                min_distance = distance
                nearest_rider = rider

        return nearest_rider

    @staticmethod
    def assign_delivery(order_id):
        try:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(id=order_id)
                if order.status != 'pending':
                    raise ValueError('Order is not pending')
                rider = DeliveryService.find_nearest_available_rider(
                    float(order.pickup_lat), float(order.pickup_lng)
                )
                if not rider:
                    raise Exception('No available riders found !!')

                delivery = Delivery.objects.create(
                    order=order,
                    rider=rider,
                    status='assigned'
                )

                rider.current_status = 'busy'
                rider.save()

                order.status = 'assigned'
                order.save()

                rider_service.add_active_delivery(str(rider.id), str(delivery.id))
                event_service.create_event(
                    delivery_id=delivery.id,
                    order_id = order.id,
                    rider_id = rider.id,
                    event_type= EventTypes.RIDER_ASSIGNED,
                    event_data={
                        'rider_name': rider.name,
                        'rider_phone': rider.phone
                    }
                )
                return delivery
        except Exception as e:
            raise e

    @staticmethod
    def update_delivery_status(delivery_id, new_status, location=None):
        try:
            with transaction.atomic():
                delivery = Delivery.objects.select_for_update().get(id=delivery_id)
                old_status = delivery.status
                deliveyr_status = new_status

                if new_status == 'completed'
                    delivery.completed_at = timezone.now()
                    rider_service.remove_active_delivery(str(delivery.rider.id), str(delivery.id))
                    delivery.rider.current_status = 'available'
                    delivery.rider.save()

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
                return delivery

        except Exception as e:
            raise e

delivery_service = DeliveryService()
