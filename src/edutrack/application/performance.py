from calendar import monthrange
from datetime import UTC, datetime
from uuid import UUID

from edutrack.infrastructure.db.models import Grade
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class PerformanceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_performance(self, student_id: UUID, month: int, year: int):
        """Получить успеваемость студента за месяц."""
        # Проверяем, что месяц валидный
        if month < 1 or month > 12:
            raise ValueError("Месяц должен быть от 1 до 12")

        # Вычисляем начало и конец месяца
        start_date = datetime(year, month, 1, tzinfo=UTC)
        _, last_day = monthrange(year, month)
        end_date = datetime(year, month, last_day, 23, 59, 59, tzinfo=UTC)

        # Получаем все оценки за месяц
        from edutrack.infrastructure.db.models import Lesson, Subject
        stmt = (
            select(Grade, Lesson, Subject)
            .join(Lesson, Grade.lesson_id == Lesson.id)
            .join(Subject, Lesson.subject_id == Subject.id)
            .where(
                Grade.student_id == student_id,
                Grade.created_at >= start_date,
                Grade.created_at <= end_date
            )
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        # Группируем по предметам
        from collections import defaultdict
        subject_stats = defaultdict(lambda: {"grades": [], "subject_id": None, "subject_name": None})

        for grade, _lesson, subject in rows:
            subject_id = subject.id
            subject_name = subject.name

            if subject_stats[subject_id]["subject_id"] is None:
                subject_stats[subject_id]["subject_id"] = subject_id
                subject_stats[subject_id]["subject_name"] = subject_name

            subject_stats[subject_id]["grades"].append(grade.value)

        # Формируем результат
        result = []
        for _subject_id, stats in subject_stats.items():
            grades_values = stats["grades"]
            avg_grade = sum(grades_values) / len(grades_values) if grades_values else None

            result.append({
                "subject_id": stats["subject_id"],
                "subject_name": stats["subject_name"],
                "grade_count": len(grades_values),
                "average_grade": round(avg_grade, 2) if avg_grade else None,
                "grades": grades_values,
            })

        return result
