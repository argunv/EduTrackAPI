from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from edutrack.infrastructure.repositories.sqlalchemy import (
    SqlAlchemyUserRepository,
    SqlAlchemyStudentRepository,
)
from edutrack.infrastructure.services.security import hash_password


class StudentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = SqlAlchemyUserRepository(session)
        self.students = SqlAlchemyStudentRepository(session)

    async def create_student(
        self,
        email: str,
        full_name: str,
        password: str,
        school_id: UUID,
        class_id: UUID | None = None,
    ):
        user = await self.users.create_user(email=email, full_name=full_name, password_hash=hash_password(password), role="student")
        student = await self.students.create_student(user_id=user.id, school_id=school_id)
        if class_id:
            await self.students.assign_to_class(student_id=student.id, class_id=class_id)
        await self.session.commit()
        return student

    async def get(self, student_id: UUID):
        return await self.students.get(student_id)





