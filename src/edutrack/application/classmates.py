from uuid import UUID

from edutrack.infrastructure.db.models import ClassStudent, Student
from edutrack.infrastructure.repositories.sqlalchemy import SqlAlchemyStudentRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class ClassmatesService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.students = SqlAlchemyStudentRepository(session)

    async def get_classmates(self, student_id: UUID):
        """Получить список одногруппников студента."""
        # Получаем студента с его классами
        student = await self.students.get(student_id)
        if not student:
            return []

        # Получаем все классы студента
        stmt = (
            select(ClassStudent.class_id)
            .where(ClassStudent.student_id == student_id)
        )
        class_ids = await self.session.scalars(stmt)
        class_ids_list = list(class_ids.all())

        if not class_ids_list:
            return []

        # Получаем всех студентов из этих классов
        from edutrack.infrastructure.db.models import User
        stmt = (
            select(Student)
            .join(ClassStudent, Student.id == ClassStudent.student_id)
            .where(
                ClassStudent.class_id.in_(class_ids_list),
                Student.id != student_id  # Исключаем самого студента
            )
            .options(
                selectinload(Student.user).selectinload(User.user_profile)
            )
        )
        classmates = await self.session.scalars(stmt)
        return list(classmates.unique().all())
