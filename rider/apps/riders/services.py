import json
from typing import Any, Dict, Optional

from infrastructure.cache import RedisClient

redis_client = RedisClient().client


def set_rider_location(rider_id: str, location_data: Dict[str, Any], ttl: int = 300):
    key = f"rider:location:{rider_id}"
    redis_client.setex(key, ttl, json.dumps(location_data))


def get_rider_location(rider_id: str) -> Optional[Dict[str, Any]]:
    key = f"rider:location:{rider_id}"
    data = redis_client.get(key)
    if data:
        return json.loads(data)
    else:
        return None


# Active Delivery-Rider Cache methods:
def add_active_delivery(rider_id: str, delivery_id: str, ttl: int = 7200):
    key = f"rider:active_deliveries:{rider_id}"
    redis_client.sadd(key, delivery_id)
    redis_client.expire(key, ttl)


def remove_active_delivery(rider_id: str, delivery_id: str):
    key = f"rider:active_deliveries:{rider_id}"
    redis_client.srem(key, delivery_id)


def get_active_deliveries(rider_id: str) -> Optional[Set[str]]:
    key = f"rider:active_deliveries:{rider_id}"
    data = redis_client.smembers(key)
    if data:
        return data
    return None


def clear_active_deliveries(rider_id: str):
    key = f"rider:active_deliveries:{rider_id}"
    redis_client.delete(key)
