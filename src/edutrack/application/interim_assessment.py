from uuid import UUID

from edutrack.infrastructure.repositories.sqlalchemy import SqlAlchemyInterimAssessmentRepository
from sqlalchemy.ext.asyncio import AsyncSession


class InterimAssessmentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.assessments = SqlAlchemyInterimAssessmentRepository(session)

    async def get_by_student(self, student_id: UUID, school_year: int | None = None):
        """Получить оценки за промежуточную аттестацию для студента."""
        assessments = await self.assessments.get_by_student(student_id, school_year)
        return list(assessments)
