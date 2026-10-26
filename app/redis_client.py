import logging
import redis
from app.config import settings
logger = logging.getLogger(__name__)
try:
    redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=1)
    redis_client.ping()
except Exception as exc:
    logger.warning("Redis unavailable at startup; Redis-backed features will fail closed gracefully: %s", exc)
    redis_client = None

def get_redis():
    if redis_client is None:
        raise RuntimeError("Redis is unavailable. Start Redis and verify REDIS_URL.")
    return redis_client
