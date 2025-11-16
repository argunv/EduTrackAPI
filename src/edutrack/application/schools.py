from sqlalchemy.ext.asyncio import AsyncSession

from edutrack.infrastructure.cache.redis import get_cache, set_cache, invalidate
from edutrack.infrastructure.repositories.sqlalchemy import SqlAlchemySchoolRepository

SCHOOLS_CACHE_KEY = "cache:schools"
SCHOOLS_TTL = 600  # 10 минут


class SchoolService:
    def __init__(self, session: AsyncSession):
        self.repo = SqlAlchemySchoolRepository(session)
        self.session = session

    async def create_school(self, name: str, address: str | None):
        school = await self.repo.create_school(name=name, address=address)
        await self.session.commit()
        await invalidate(SCHOOLS_CACHE_KEY)
        return school

    async def list_schools(self):
        cached = await get_cache(SCHOOLS_CACHE_KEY)
        if cached:
            return cached
        schools = await self.repo.list_schools()
        data = [{"id": str(s.id), "name": s.name, "address": s.address} for s in schools]
        await set_cache(SCHOOLS_CACHE_KEY, data, ttl_seconds=SCHOOLS_TTL)
        return data





