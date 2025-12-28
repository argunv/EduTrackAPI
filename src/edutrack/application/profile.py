from datetime import date
from uuid import UUID

from edutrack.infrastructure.repositories.sqlalchemy import SqlAlchemyUserRepository
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class ProfileService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = SqlAlchemyUserRepository(session)

    async def get_profile(self, user_id: UUID):
        """Получить профиль пользователя."""
        from edutrack.infrastructure.db.models import User
        stmt = select(User).where(User.id == user_id).options(selectinload(User.user_profile))
        user = await self.session.scalar(stmt)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
        return user

    async def update_profile(
        self,
        user_id: UUID,
        full_name: str | None = None,
        date_of_birth: date | None = None,
        show_birthday: bool | None = None,
        avatar_url: str | None = None,
    ):
        """Обновить профиль пользователя."""
        user = await self.users.update_profile(
            user_id=user_id,
            full_name=full_name,
            date_of_birth=date_of_birth,
            show_birthday=show_birthday,
            avatar_url=avatar_url,
        )
        await self.session.commit()
        return user
