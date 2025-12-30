import logging

import redis
from django.conf import settings
from django.core.cache import cache
from django_redis import get_redis_connection

logger = logging.getLogger(__name__)

redis_conn = get_redis_connection("default")


class RedisClient:
    def __init__(self):
        self.client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )


def check_cache_connection():
    # Check if the cache is configured correctly
    if not settings.CACHES:
        logger.error("CACHES setting is not configured !!")
        raise ValueError("CACHES setting is not configured")

    # Check if the cache is connected properly or not
    try:
        if cache.ensure_connection():
            logger.info("Cache connection established")
        else:
            logger.error("Cache connection failed !!")
    except Exception as e:
        logger.error(f"Cache connection error: {e}")
        raise ValueError(f"Cache connection error: {e}")


def get_cache_key_value(key):
    try:
        value = cache.get(key)
        if value is None:
            logger.warning(f"Cache miss for key: {key}")
        else:
            logger.info(f"Cache hit for key: {key}")
        return value
    except Exception as e:
        logger.error(f"Cache get error for key: {key}, error: {e}")
        raise ValueError(f"Cache get error for key: {key}, error: {e}")


def set_cache_key(key, value):
    try:
        cache.set(key, value)
        logger.info(f"Cache set for key: {key}")
    except Exception as e:
        logger.error(f"Cache set error for key: {key}, error: {e}")
        raise ValueError(f"Cache set error for key: {key}, error: {e}")


def delete_cache_key(key):
    try:
        cache.delete(key)
        logger.info(f"Cache deleted for key: {key}")
    except Exception as e:
        logger.error(f"Cache delete error for key: {key}, error: {e}")
        raise ValueError(f"Cache delete error for key: {key}, error: {e}")


def clear_cache():
    try:
        cache.clear()
        logger.info("Cache cleared")
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        raise ValueError(f"Cache clear error: {e}")


def flush_cache():
    try:
        cache.flush()
        logger.info("Cache flushed")
    except Exception as e:
        logger.error(f"Cache flush error: {e}")
        raise ValueError(f"Cache flush error: {e}")


def update_key_ttl(key, ttl):
    try:
        cache.expire(key, ttl)
        logger.info(f"Cache TTL updated for key: {key}")
    except Exception as e:
        logger.error(f"Cache TTL update error for key: {key}, error: {e}")
        raise ValueError(f"Cache TTL update error for key: {key}, error: {e}")
