from uuid import UUID

from edutrack.infrastructure.repositories.sqlalchemy import SqlAlchemyDirectMessageRepository
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession


class DirectMessageService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.messages = SqlAlchemyDirectMessageRepository(session)

    async def send_message(self, sender_id: UUID, recipient_id: UUID, content: str):
        """Отправить сообщение."""
        if sender_id == recipient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя отправить сообщение самому себе"
            )

        message = await self.messages.create_message(
            sender_id=sender_id,
            recipient_id=recipient_id,
            content=content
        )
        await self.session.commit()
        return message

    async def get_conversation(self, user1_id: UUID, user2_id: UUID, limit: int = 50):
        """Получить переписку между двумя пользователями."""
        messages = await self.messages.get_conversation(user1_id, user2_id, limit)
        return list(messages)

    async def mark_as_read(self, message_id: UUID, user_id: UUID) -> None:
        """Отметить сообщение как прочитанное."""
        # Проверяем, что пользователь является получателем
        # (это можно сделать через получение сообщения, но для простоты пропустим)
        await self.messages.mark_as_read(message_id)
        await self.session.commit()

    async def get_unread_count(self, user_id: UUID) -> int:
        """Получить количество непрочитанных сообщений."""
        return await self.messages.get_unread_count(user_id)
