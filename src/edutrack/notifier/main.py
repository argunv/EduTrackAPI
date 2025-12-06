import asyncio
import json
import logging
from aio_pika import connect_robust, IncomingMessage

from edutrack.config.settings import get_settings
from edutrack.infrastructure.db.database import SessionLocal
from edutrack.infrastructure.repositories.sqlalchemy import SqlAlchemyEmailOutboxRepository
from edutrack.infrastructure.email.sender import send_email


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("edutrack.notifier")
settings = get_settings()


async def process_message(message: IncomingMessage):
    async with message.process():
        data = json.loads(message.body.decode())
        outbox_id = data.get("outbox_id")
        if not outbox_id:
            logger.error("Message without outbox_id, skipping")
            return

        async with SessionLocal() as session:
            repo = SqlAlchemyEmailOutboxRepository(session)
            entry = await repo.get_pending(outbox_id)
            if not entry:
                logger.warning("Outbox entry %s not found", outbox_id)
                return
            try:
                await send_email(entry.recipients, entry.subject, entry.body)
                await repo.mark_sent(entry.id)
                await session.commit()
                logger.info("Email sent for outbox %s", outbox_id)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Failed to send email for outbox %s", outbox_id)
                await repo.mark_failed(entry.id, str(exc))
                await session.commit()
                # allow retry via queue redelivery
                raise


async def main():
    connection = await connect_robust(settings.rabbitmq_url)
    channel = await connection.channel()
    queue = await channel.declare_queue(settings.rabbitmq_email_queue, durable=True)
    await queue.consume(process_message, no_ack=False)
    logger.info("Notifier started, waiting for messages...")
    try:
        await asyncio.Future()
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())





