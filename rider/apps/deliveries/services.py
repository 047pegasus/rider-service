import json
from typing import Any, Dict, Optional

from infrastructure.cache import redis_client


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
            return json.loads(data)
        return None


delivery_service = DeliveryService()
