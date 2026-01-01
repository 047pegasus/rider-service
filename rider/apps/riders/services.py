import json
from datetime import datetime
from typing import Any, Dict, Optional,Set

from confluent_kafka.error import KafkaError
from infrastructure.cache import redis_client
from infrastructure.kafka_client import kafka_client

from apps.deliveries.constants import KAFKA_TOPICS

from .models import Rider, RiderLocation


class RiderService:
    def set_rider_location(
        self, rider_id: str, location_data: Dict[str, Any], ttl: int = 300
    ):
        key = f"rider:location:{rider_id}"
        redis_client.setex(key, ttl, json.dumps(location_data))

    def get_rider_location(self, rider_id: str) -> Optional[Dict[str, Any]]:
        key = f"rider:location:{rider_id}"
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        else:
            return None

    # Active Delivery-Rider Cache methods:
    def add_active_delivery(self, rider_id: str, delivery_id: str, ttl: int = 7200):
        key = f"rider:active_deliveries:{rider_id}"
        redis_client.sadd(key, delivery_id)
        redis_client.expire(key, ttl)

    def remove_active_delivery(self, rider_id: str, delivery_id: str):
        key = f"rider:active_deliveries:{rider_id}"
        redis_client.srem(key, delivery_id)

    def get_active_deliveries(self, rider_id: str) -> Optional[Set[str]]:
        key = f"rider:active_deliveries:{rider_id}"
        data = redis_client.smembers(key)
        if data:
            return data
        else:
            return None

    def clear_active_deliveries(self, rider_id: str):
        key = f"rider:active_deliveries:{rider_id}"
        redis_client.delete(key)

    ## Rider Location Tracking Helper Methods
    def update_rider_location(self, rider_id, location_data, delivery_id=None):
        try:
            # rider = Rider.objects.get(id=rider_id)
            location = RiderLocation.objects.create(
                rider_id=rider_id,
                delivery_id=delivery_id,
                lat=location_data["lat"],
                lng=location_data["lng"],
                accuracy=location_data.get("accuracy"),
                speed=location_data.get("speed"),
                heading=location_data.get("heading"),
                battery_level=location_data.get("battery_level"),
            )
            cache_data_value = {
                "lat": float(location_data["lat"]),
                "lng": float(location_data["lng"]),
                "accuracy": location_data.get("accuracy"),
                "speed": location_data.get("speed"),
                "heading": location_data.get("heading"),
                "battery_level": location_data.get("battery_level"),
                "timestamp": datetime.now().isoformat(),
            }

            self.set_rider_location(str(rider_id), cache_data_value)

            kafka_msg = {
                "rider_id": str(rider_id),
                "delivery_id": str(delivery_id) if delivery_id else None,
                "location": cache_data_value,
                "timestamp": datetime.now().isoformat(),
            }

            topic = (KAFKA_TOPICS.get("RIDER_LOCATION_UPDATE"),)
            kafka_client.publish(topic, kafka_msg)

            return location

        except Rider.DoesNotExist:
            print(f"Rider with ID {rider_id} does not exist")
            return None
        except Exception as e:
            print(f"Error updating rider location: {e}")
            return None

    def get_rider_current_location(self, rider_id):
        try:
            location = self.get_rider_location(str(rider_id))
            if location:
                return location
            try:
                db_location = RiderLocation.objects.filter(rider_id=rider_id).latest(
                    "timestamp"
                )
                return {
                    "lat": float(db_location.lat),
                    "lng": float(db_location.lng),
                    "timestamp": db_location.timestamp.isoformat(),
                }
            except RiderLocation.DoesNotExist:
                return None
            except Exception as e:
                return None
        except Rider.DoesNotExist:
            return None
        except Exception as e:
            return None

    def get_rider_location_history(self, rider_id):
        try:
            locations = RiderLocation.objects.filter(rider_id=rider_id).order_by(
                "-timestamp"
            )[:limit]
            return [
                {
                    "lat": float(location.lat),
                    "lng": float(location.lng),
                    "timestamp": location.timestamp.isoformat(),
                }
                for location in locations
            ]
        except RiderLocation.DoesNotExist:
            return []
        except Exception as e:
            return None


rider_service = RiderService()
