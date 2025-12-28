import logging
import secrets
from datetime import UTC, datetime, timedelta

from edutrack.infrastructure.email.sender import send_email
from edutrack.infrastructure.repositories.sqlalchemy import (
    SqlAlchemyPasswordResetTokenRepository,
    SqlAlchemyUserRepository,
)
from edutrack.infrastructure.services.security import hash_password
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class PasswordResetService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = SqlAlchemyUserRepository(session)
        self.tokens = SqlAlchemyPasswordResetTokenRepository(session)

    async def request_reset(self, email: str) -> None:
        """Запросить восстановление пароля."""
        user = await self.users.get_by_email(email)
        if not user:
            # Не раскрываем, существует ли пользователь
            return

        # Генерируем токен
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(hours=24)

        await self.tokens.create_token(user_id=user.id, token=token, expires_at=expires_at)
        await self.session.commit()

        # Отправляем email с токеном
        reset_url = f"https://edutrack.local/reset-password?token={token}"
        try:
            await send_email(
                recipients=[email],
                subject="Восстановление пароля",
                body=f"Для восстановления пароля перейдите по ссылке: {reset_url}\n\nСсылка действительна 24 часа."
            )
            logger.info(f"Password reset email sent successfully to {email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {e}", exc_info=True)
            # Не поднимаем исключение, чтобы не раскрывать информацию о существовании пользователя
            # Токен уже создан, пользователь может запросить новый

    async def reset_password(self, token: str, new_password: str) -> None:
        """Сбросить пароль по токену."""
        reset_token = await self.tokens.get_by_token(token)
        if not reset_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Недействительный или истекший токен"
            )

        # Обновляем пароль
        user = await self.users.get_by_id(reset_token.user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

        user.password_hash = hash_password(new_password)
        await self.tokens.mark_as_used(reset_token.id)
        await self.session.commit()
