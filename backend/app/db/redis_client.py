import redis
from urllib.parse import urlparse
from ..core.config import settings


def get_redis_client() -> redis.Redis:
    """Return a Redis client.

    Prefers REDIS_URL if provided (e.g., Upstash or Redis Cloud). Falls back to host/port.
    """
    if settings.REDIS_URL:
        return redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)


