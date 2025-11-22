from edutrack.infrastructure.cache.redis import get_cache, invalidate, set_cache
from edutrack.infrastructure.db import models
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

SUBJECTS_CACHE_KEY = "cache:subjects"
SUBJECTS_TTL = 600


class SubjectService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_subject(self, name: str) -> models.Subject:
        subject = models.Subject(name=name)
        self.session.add(subject)
        await self.session.commit()
        await invalidate(SUBJECTS_CACHE_KEY)
        return subject

    async def list_subjects(self):
        cached = await get_cache(SUBJECTS_CACHE_KEY)
        if cached:
            return cached
        result = await self.session.scalars(select(models.Subject).order_by(models.Subject.name))
        subjects = result.all()
        data = [{"id": str(s.id), "name": s.name} for s in subjects]
        await set_cache(SUBJECTS_CACHE_KEY, data, ttl_seconds=SUBJECTS_TTL)
        return data
