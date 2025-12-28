import asyncio
import json
import logging
import signal

from aio_pika import IncomingMessage, connect_robust
from aio_pika.exceptions import AMQPConnectionError

from edutrack.config.settings import get_settings
from edutrack.infrastructure.db.database import SessionLocal, engine
from edutrack.infrastructure.email.sender import send_email
from edutrack.infrastructure.repositories.sqlalchemy import SqlAlchemyEmailOutboxRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("edutrack.notifier")
settings = get_settings()

# Глобальные переменные для graceful shutdown
shutdown_event = asyncio.Event()
connection = None
channel = None
processing_tasks: set[asyncio.Task] = set()


async def process_message(message: IncomingMessage, max_retries: int = 3):
    """Обработать сообщение из очереди с retry логикой."""
    task = asyncio.current_task()
    if task:
        processing_tasks.add(task)

    try:
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

                # Retry логика для отправки email
                for attempt in range(1, max_retries + 1):
                    try:
                        await send_email(entry.recipients, entry.subject, entry.body)
                        await repo.mark_sent(entry.id)
                        await session.commit()
                        logger.info("Email sent for outbox %s (attempt %d)", outbox_id, attempt)
                        return
                    except Exception as exc:
                        logger.warning(
                            "Failed to send email for outbox %s (attempt %d/%d): %s",
                            outbox_id,
                            attempt,
                            max_retries,
                            str(exc),
                        )
                        if attempt < max_retries:
                            # Экспоненциальная задержка перед повтором
                            await asyncio.sleep(2 ** attempt)
                        else:
                            # Все попытки исчерпаны
                            logger.error(
                                "All retry attempts failed for outbox %s: %s",
                                outbox_id,
                                str(exc),
                                exc_info=True,
                            )
                            await repo.mark_failed(entry.id, str(exc))
                            await session.commit()
                            # Не поднимаем исключение, чтобы сообщение не вернулось в очередь
    except Exception as exc:
        logger.error(f"Unexpected error processing message: {exc}", exc_info=True)
        # Поднимаем исключение для повторной доставки сообщения
        raise
    finally:
        if task:
            processing_tasks.discard(task)


async def connect_with_retry(max_retries: int = 5, initial_delay: float = 1.0):
    """Подключиться к RabbitMQ с retry логикой."""
    global connection, channel

    for attempt in range(1, max_retries + 1):
        try:
            connection = await connect_robust(settings.rabbitmq_url)
            channel = await connection.channel()
            queue = await channel.declare_queue(settings.rabbitmq_email_queue, durable=True)
            await queue.consume(process_message, no_ack=False)
            logger.info("Connected to RabbitMQ successfully")
            return queue
        except AMQPConnectionError as e:
            if attempt < max_retries:
                delay = initial_delay * (2 ** (attempt - 1))
                logger.warning(
                    "Failed to connect to RabbitMQ (attempt %d/%d): %s. Retrying in %.1f seconds...",
                    attempt,
                    max_retries,
                    str(e),
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error("Failed to connect to RabbitMQ after %d attempts", max_retries)
                raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to RabbitMQ: {e}", exc_info=True)
            raise


async def shutdown_handler():
    """Обработчик graceful shutdown."""
    logger.info("Начало graceful shutdown notifier...")
    shutdown_event.set()

    # Ждем завершения обработки текущих сообщений (максимум 30 секунд)
    if processing_tasks:
        logger.info(f"Ожидание завершения {len(processing_tasks)} активных задач...")
        try:
            await asyncio.wait_for(
                asyncio.gather(*processing_tasks, return_exceptions=True),
                timeout=30.0,
            )
            logger.info("Все активные задачи завершены")
        except TimeoutError:
            logger.warning("Таймаут ожидания завершения задач, принудительное завершение")

    # Закрываем соединения
    # Используем глобальные переменные connection и channel
    if 'channel' in globals() and channel and not channel.is_closed:
        try:
            await channel.close()
            logger.info("RabbitMQ канал закрыт")
        except Exception as e:
            logger.warning(f"Ошибка при закрытии канала: {e}")

    if 'connection' in globals() and connection and not connection.is_closed:
        try:
            # Для robust connection нужно сначала отключить автоматическое переподключение
            if hasattr(connection, 'closing'):
                connection.closing = True
            await connection.close()
            logger.info("RabbitMQ соединение закрыто")
        except Exception as e:
            logger.warning(f"Ошибка при закрытии соединения: {e}")

    # Закрываем соединения с БД
    try:
        await engine.dispose()
        logger.info("Соединения с БД закрыты")
    except Exception as e:
        logger.error(f"Ошибка при закрытии соединений с БД: {e}", exc_info=True)

    logger.info("Graceful shutdown notifier завершен")


async def main():
    """Основная функция notifier."""
    # Настройка обработчиков сигналов
    def signal_handler(sig):
        logger.info(f"Получен сигнал {sig.name}, инициируем graceful shutdown...")
        asyncio.create_task(shutdown_handler())

    loop = asyncio.get_event_loop()
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
    except NotImplementedError:
        logger.warning("Обработчики сигналов не поддерживаются на этой платформе")

    try:
        # Подключаемся к RabbitMQ с retry
        await connect_with_retry()
        logger.info("Notifier started, waiting for messages...")

        # Ждем сигнала завершения
        await shutdown_event.wait()
    except KeyboardInterrupt:
        logger.info("Получен KeyboardInterrupt, инициируем graceful shutdown...")
        await shutdown_handler()
    except Exception as e:
        logger.error(f"Критическая ошибка в notifier: {e}", exc_info=True)
        await shutdown_handler()
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Notifier остановлен")
