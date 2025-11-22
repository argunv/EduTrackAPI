from aio_pika import connect_robust
from edutrack.config.settings import get_settings
from edutrack.infrastructure.cache.redis import redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def check_health(session: AsyncSession):
    settings = get_settings()
    db_ok = False
    redis_ok = False
    rabbit_ok = False

    try:
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    try:
        await redis.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    try:
        conn = await connect_robust(settings.rabbitmq_url, timeout=2)
        await conn.close()
        rabbit_ok = True
    except Exception:
        rabbit_ok = False

    overall = db_ok and redis_ok and rabbit_ok
    return {"status": "ok" if overall else "degraded", "db": db_ok, "redis": redis_ok, "rabbitmq": rabbit_ok}
