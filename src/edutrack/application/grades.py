from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from edutrack.infrastructure.cache.redis import get_cache, set_cache, invalidate
from edutrack.infrastructure.repositories.sqlalchemy import SqlAlchemyGradeRepository

GRADES_TTL = 60  # 1 минута


class GradeService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = SqlAlchemyGradeRepository(session)

    def _cache_key(self, student_id: UUID) -> str:
        return f"cache:grades:{student_id}"

    async def create_grade(self, student_id: UUID, lesson_id: UUID, value: int, comment: str | None):
        grade = await self.repo.create_grade(student_id=student_id, lesson_id=lesson_id, value=value, comment=comment)
        await self.session.commit()
        await invalidate(self._cache_key(student_id))
        return grade

    async def list_grades(self, student_id: UUID):
        key = self._cache_key(student_id)
        cached = await get_cache(key)
        if cached:
            return cached
        grades = await self.repo.list_for_student(student_id)
        data = [
            {
                "id": str(g.id),
                "lesson_id": str(g.lesson_id),
                "value": g.value,
                "comment": g.comment,
                "created_at": g.created_at.isoformat(),
            }
            for g in grades
        ]
        await set_cache(key, data, ttl_seconds=GRADES_TTL)
        return data





