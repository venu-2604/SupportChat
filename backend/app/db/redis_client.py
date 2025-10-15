import redis
from ..core.config import settings


def get_redis_client() -> redis.Redis:
    return redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)


