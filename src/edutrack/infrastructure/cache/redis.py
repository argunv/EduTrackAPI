import json
from typing import Any, Optional
from redis.asyncio import Redis

from edutrack.config.settings import get_settings


settings = get_settings()
redis = Redis.from_url(settings.redis_url, decode_responses=True)


async def get_cache(key: str) -> Optional[Any]:
    raw = await redis.get(key)
    return json.loads(raw) if raw else None


async def set_cache(key: str, value: Any, ttl_seconds: int) -> None:
    await redis.set(key, json.dumps(value, default=str), ex=ttl_seconds)


async def invalidate(key: str) -> None:
    await redis.delete(key)





