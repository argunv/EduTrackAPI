import logging
from uuid import UUID

from edutrack.infrastructure.repositories.sqlalchemy import (
    SqlAlchemyStudentRepository,
    SqlAlchemyUserRepository,
)
from edutrack.infrastructure.services.avatar import generate_avatar_url
from edutrack.infrastructure.services.security import hash_password
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


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
        user = await self.users.create_user(
            email=email, full_name=full_name, password_hash=hash_password(password), roles=["student"]
        )
        
        # Генерируем аватар из имени пользователя
        try:
            avatar_url = generate_avatar_url(name=full_name, size=200)
            # Создаем профиль с аватаром
            await self.users.update_profile(user_id=user.id, avatar_url=avatar_url)
            logger.info(f"Аватар сгенерирован для пользователя {user.id}")
        except Exception as e:
            # Не блокируем создание пользователя, если аватар не удалось сгенерировать
            logger.warning(f"Не удалось сгенерировать аватар для пользователя {user.id}: {e}")
        
        student = await self.students.create_student(user_id=user.id, school_id=school_id)
        if class_id:
            await self.students.assign_to_class(student_id=student.id, class_id=class_id)
        await self.session.commit()
        return student

    async def get(self, student_id: UUID):
        return await self.students.get(student_id)
