import json
from datetime import datetime
from typing import Any, Dict, Optional, Set
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

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
        """
        Get rider location from cache first, then fallback to database.
        This ensures location persists across restarts.
        """
        key = f"rider:location:{rider_id}"
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        else:
            # Fallback to database - get latest location
            return self.get_rider_current_location(rider_id)

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

            topic = KAFKA_TOPICS.get("RIDER_LOCATION_UPDATE")
            if topic:
                # Use rider_id as partition key for consistent ordering per rider
                kafka_client.publish(topic, kafka_msg, key=str(rider_id))

            # Send WebSocket notification for location updates
            if delivery_id:
                # Notify order channel about rider location
                channel_layer = get_channel_layer()
                if channel_layer:
                    # Find order for this delivery
                    from apps.deliveries.models import Delivery
                    try:
                        delivery = Delivery.objects.get(id=delivery_id)
                        async_to_sync(channel_layer.group_send)(
                            f"order_{delivery.order.id}",
                            {
                                "type": "location_update",
                                "data": {
                                    "rider_id": str(rider_id),
                                    "location": cache_data_value,
                                    "delivery_id": str(delivery_id)
                                }
                            }
                        )
                    except Delivery.DoesNotExist:
                        pass
                
                # Notify rider channel
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        f"rider_{rider_id}",
                        {
                            "type": "location_update",
                            "data": {
                                "location": cache_data_value,
                                "delivery_id": str(delivery_id)
                            }
                        }
                    )

            return location

        except Rider.DoesNotExist:
            print(f"Rider with ID {rider_id} does not exist")
            return None
        except Exception as e:
            print(f"Error updating rider location: {e}")
            return None

    def get_rider_current_location(self, rider_id):
        """
        Get rider's current location from database (latest RiderLocation entry).
        This is the source of truth for persistent location.
        """
        try:
            # First check if there's an active delivery with last location
            from apps.deliveries.models import Delivery
            active_delivery = Delivery.objects.filter(
                rider_id=rider_id,
                status__in=['assigned', 'accepted', 'in_progress', 'collected']
            ).exclude(
                last_location_lat__isnull=True
            ).order_by('-updated_at').first()
            
            if active_delivery and active_delivery.last_location_lat:
                return {
                    "lat": float(active_delivery.last_location_lat),
                    "lng": float(active_delivery.last_location_lng),
                    "timestamp": active_delivery.updated_at.isoformat(),
                }
            
            # Fallback to latest RiderLocation entry
            try:
                db_location = RiderLocation.objects.filter(rider_id=rider_id).latest(
                    "timestamp"
                )
                return {
                    "lat": float(db_location.lat),
                    "lng": float(db_location.lng),
                    "timestamp": db_location.timestamp.isoformat(),
                    "accuracy": float(db_location.accuracy) if db_location.accuracy else None,
                    "speed": float(db_location.speed) if db_location.speed else None,
                    "heading": float(db_location.heading) if db_location.heading else None,
                    "battery_level": db_location.battery_level,
                }
            except RiderLocation.DoesNotExist:
                return None
            except Exception as e:
                print(f"Error getting location from DB: {e}")
                return None
        except Exception as e:
            print(f"Error in get_rider_current_location: {e}")
            return None

    def get_rider_location_history(self, rider_id, limit=10):
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
