from uuid import UUID

from edutrack.infrastructure.cache.redis import get_cache, invalidate, set_cache
from edutrack.infrastructure.repositories.sqlalchemy import SqlAlchemyClassRepository
from sqlalchemy.ext.asyncio import AsyncSession

CLASSES_TTL = 600


class ClassService:
    def __init__(self, session: AsyncSession):
        self.repo = SqlAlchemyClassRepository(session)
        self.session = session

    def _cache_key(self, school_id: UUID | None) -> str:
        return f"cache:classes:{school_id or 'all'}"

    async def create_class(self, school_id: UUID, name: str, grade_level: int):
        class_ = await self.repo.create_class(school_id=school_id, name=name, grade_level=grade_level)
        await self.session.commit()
        await invalidate(self._cache_key(school_id))
        return class_

    async def list_classes(self, school_id: UUID | None):
        key = self._cache_key(school_id)
        cached = await get_cache(key)
        if cached:
            return cached
        classes = await self.repo.list_classes(school_id)
        data = [
            {"id": str(c.id), "school_id": str(c.school_id), "name": c.name, "grade_level": c.grade_level}
            for c in classes
        ]
        await set_cache(key, data, ttl_seconds=CLASSES_TTL)
        return data
