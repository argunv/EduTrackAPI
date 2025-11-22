from collections.abc import Sequence
from uuid import UUID

from edutrack.infrastructure.queue.publisher import EmailPublisher
from edutrack.infrastructure.repositories.sqlalchemy import (
    SqlAlchemyEmailOutboxRepository,
    SqlAlchemyMessageRepository,
)
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession


class MessageService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.messages = SqlAlchemyMessageRepository(session)
        self.outbox = SqlAlchemyEmailOutboxRepository(session)
        self.publisher = EmailPublisher()

    async def create_message(self, sender_id: UUID, subject: str, body: str, recipient_user_ids: list[UUID]):
        message = await self.messages.create_message(sender_id=sender_id, subject=subject, body=body)
        if recipient_user_ids:
            await self.messages.add_recipients(message_id=message.id, recipients=recipient_user_ids)
        await self.session.commit()
        return message

    async def enqueue_email(self, message_id: UUID, recipients_emails: Sequence[str]):
        message = await self.messages.get(message_id)
        if not message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
        outbox_entry = await self.outbox.enqueue(
            message_id=message_id,
            recipients=list(recipients_emails),
            subject=message.subject,
            body=message.body,
        )
        await self.session.commit()
        await self.publisher.publish_outbox(str(outbox_entry.id))
        return outbox_entry
