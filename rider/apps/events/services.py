import json

from infrastructure.cache import RedisClient

RedisClient = RedisClient().client


# Event Idempotency
def mark_event_processed(event_id: str, ttl: int = 86400):
    key = f"event:processed:{event_id}"
    RedisClient.setex(key, ttl, json.dumps({"status": "processed"}))


def is_event_processed(event_id: str) -> bool:
    key = f"event:processed:{event_id}"
    data = RedisClient.exists(key)
    if data:
        return json.loads(data)["status"] == "processed"
    return False
