import json
import logging
from typing import Any

from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import ConnectionError, RedisError

from edutrack.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Используем connection pool для лучшей производительности
pool = ConnectionPool.from_url(settings.redis_url, decode_responses=True, max_connections=10)
redis = Redis(connection_pool=pool)


async def get_cache(key: str) -> Any | None:
    """Получить значение из кеша. Возвращает None при ошибках (graceful degradation)."""
    try:
        raw = await redis.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Ошибка декодирования JSON из кеша для ключа {key}: {e}. Удаляем поврежденный ключ.")
            # Удаляем поврежденный ключ
            try:
                await redis.delete(key)
            except Exception:
                pass
            return None
    except (ConnectionError, RedisError) as e:
        logger.warning(f"Redis недоступен при получении ключа {key}: {e}. Продолжаем без кеша.")
        return None
    except Exception as e:
        logger.error(f"Неожиданная ошибка Redis при получении ключа {key}: {e}", exc_info=True)
        return None


async def set_cache(key: str, value: Any, ttl_seconds: int) -> None:
    """Установить значение в кеш. Игнорирует ошибки (graceful degradation)."""
    try:
        await redis.set(key, json.dumps(value, default=str), ex=ttl_seconds)
    except (ConnectionError, RedisError) as e:
        logger.warning(f"Redis недоступен при установке ключа {key}: {e}. Продолжаем без кеша.")
    except Exception as e:
        logger.error(f"Неожиданная ошибка Redis при установке ключа {key}: {e}", exc_info=True)


async def invalidate(key: str) -> None:
    """Удалить ключ из кеша. Игнорирует ошибки (graceful degradation)."""
    try:
        await redis.delete(key)
    except (ConnectionError, RedisError) as e:
        logger.warning(f"Redis недоступен при удалении ключа {key}: {e}. Продолжаем без кеша.")
    except Exception as e:
        logger.error(f"Неожиданная ошибка Redis при удалении ключа {key}: {e}", exc_info=True)


async def close_redis() -> None:
    """Закрыть соединения с Redis (для graceful shutdown)."""
    try:
        await redis.aclose()
        await pool.aclose()
        logger.info("Redis соединения закрыты")
    except Exception as e:
        logger.error(f"Ошибка при закрытии Redis соединений: {e}", exc_info=True)
