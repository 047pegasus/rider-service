import json

from django.db import transaction
from infrastructure.cache import redis_client
from infrastructure.kafka_client import kafka_client

from apps.deliveries.constants import KAFKA_TOPICS

from .models import DeliveryEvent


# Event Idempotency
def mark_event_processed(event_id: str, ttl: int = 86400):
    key = f"event:processed:{event_id}"
    redis_client.setex(key, ttl, json.dumps({"status": "processed"}))


def is_event_processed(event_id: str) -> bool:
    key = f"event:processed:{event_id}"
    data = redis_client.exists(key)
    if data:
        return json.loads(data)["status"] == "processed"
    return False


class EventService:
    @staticmethod
    def create_event(
        delivery_id: str | None,
        order_id: str | None,
        rider_id: str | None,
        event_type,
        event_data=None,
        location=None,
    ):
        try:
            with transaction.atomic():
                event = DeliveryEvent.objects.create(
                    delivery_id=delivery_id,
                    order_id=order_id,
                    rider_id=rider_id,
                    event_type=event_type,
                    event_data=event_data or {},
                    location_lat=location.get("lat") if location else None,
                    location_lng=location.get("lng") if location else None,
                )

                kafka_msg = {
                    "event_id": event.id,
                    "event_type": event_type,
                    "timestamp": event.timestamp.isoformat(),
                    "delivery_id": str(delivery_id),
                    "order_id": str(order_id),
                    "rider_id": str(rider_id),
                    "data": event_data or {},
                    "location": location,
                }

                topic = KAFKA_TOPICS.get("DELIVERY_STATUS_CHANGED")
                kafka_client.publish(topic=topic, event_data=kafka_msg)
                mark_event_processed(event_id)
                return event

        except Exception as e:
            return None

    @staticmethod
    def get_delivery_events(delivery_id):
        try:
            return DeliveryEvent.objects.filter(delivery_id=delivery_id).order_by(
                "-timestamp"
            )
        except Exception as e:
            return None

    @staticmethod
    def get_order_events(order_id):
        try:
            return DeliveryEvent.objects.filter(order_id=order_id).order_by(
                "-timestamp"
            )
        except Exception as e:
            return None


event_service = EventService()
