from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from edutrack.infrastructure.cache.redis import get_cache, set_cache, invalidate
from edutrack.infrastructure.repositories.sqlalchemy import SqlAlchemyLessonRepository

SCHEDULE_TTL = 120


class LessonService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = SqlAlchemyLessonRepository(session)

    def _schedule_key(self, class_id: UUID) -> str:
        return f"cache:schedule:class:{class_id}"

    async def create_lesson(
        self,
        class_id: UUID,
        subject_id: UUID,
        teacher_id: UUID,
        topic: str,
        start_at: datetime,
        end_at: datetime,
    ):
        lesson = await self.repo.create_lesson(
            class_id=class_id,
            subject_id=subject_id,
            teacher_id=teacher_id,
            topic=topic,
            start_at=start_at,
            end_at=end_at,
        )
        await self.session.commit()
        await invalidate(self._schedule_key(class_id))
        return lesson

    async def list_schedule(self, class_id: UUID):
        key = self._schedule_key(class_id)
        cached = await get_cache(key)
        if cached:
            return cached
        lessons = await self.repo.list_for_class(class_id)
        data = [
            {
                "id": str(l.id),
                "topic": l.topic,
                "start_at": l.start_at.isoformat(),
                "end_at": l.end_at.isoformat(),
                "subject_id": str(l.subject_id),
            }
            for l in lessons
        ]
        await set_cache(key, data, ttl_seconds=SCHEDULE_TTL)
        return data





