import asyncio
import json
import logging

from aio_pika import DeliveryMode, Message, connect_robust
from aio_pika.abc import AbstractConnection, AbstractChannel

from edutrack.config.settings import get_settings

logger = logging.getLogger(__name__)


class EmailPublisher:
    """Публикатор сообщений в RabbitMQ с переиспользованием соединений."""
    
    def __init__(self):
        self.settings = get_settings()
        self._connection: AbstractConnection | None = None
        self._channel: AbstractChannel | None = None
        self._lock = asyncio.Lock()
        self._queue_name: str | None = None

    async def _ensure_connection(self) -> None:
        """Обеспечить наличие активного соединения и канала."""
        if self._connection and not self._connection.is_closed:
            if self._channel and not self._channel.is_closed:
                return
        
        async with self._lock:
            # Двойная проверка после получения блокировки
            if self._connection and not self._connection.is_closed:
                if self._channel and not self._channel.is_closed:
                    return
            
            # Закрываем старые соединения, если они есть
            if self._channel and not self._channel.is_closed:
                try:
                    await self._channel.close()
                except Exception as e:
                    logger.warning(f"Ошибка при закрытии канала: {e}")
            
            if self._connection and not self._connection.is_closed:
                try:
                    await self._connection.close()
                except Exception as e:
                    logger.warning(f"Ошибка при закрытии соединения: {e}")
            
            # Создаем новое соединение
            try:
                self._connection = await connect_robust(self.settings.rabbitmq_url)
                self._channel = await self._connection.channel()
                # Объявляем очередь один раз
                queue = await self._channel.declare_queue(
                    self.settings.rabbitmq_email_queue, 
                    durable=True
                )
                self._queue_name = queue.name
                logger.info("RabbitMQ соединение установлено")
            except Exception as e:
                logger.error(f"Ошибка при установке соединения с RabbitMQ: {e}", exc_info=True)
                self._connection = None
                self._channel = None
                raise

    async def publish_outbox(self, outbox_id: str) -> None:
        """Опубликовать сообщение в очередь."""
        try:
            await self._ensure_connection()
            
            if not self._channel or self._channel.is_closed:
                raise ConnectionError("Канал RabbitMQ недоступен")
            
            payload = json.dumps({"outbox_id": outbox_id}).encode()
            await self._channel.default_exchange.publish(
                Message(payload, delivery_mode=DeliveryMode.PERSISTENT),
                routing_key=self._queue_name or self.settings.rabbitmq_email_queue,
            )
            logger.debug(f"Сообщение опубликовано в очередь: {outbox_id}")
        except Exception as e:
            logger.error(f"Ошибка при публикации сообщения {outbox_id} в RabbitMQ: {e}", exc_info=True)
            # Сбрасываем соединение при ошибке для переподключения
            if self._channel:
                try:
                    await self._channel.close()
                except Exception:
                    pass
                self._channel = None
            if self._connection:
                try:
                    await self._connection.close()
                except Exception:
                    pass
                self._connection = None
            raise

    async def close(self) -> None:
        """Закрыть соединения (для graceful shutdown)."""
        async with self._lock:
            if self._channel and not self._channel.is_closed:
                try:
                    await self._channel.close()
                    logger.info("RabbitMQ канал закрыт")
                except Exception as e:
                    logger.warning(f"Ошибка при закрытии канала: {e}")
                self._channel = None
            
            if self._connection and not self._connection.is_closed:
                try:
                    await self._connection.close()
                    logger.info("RabbitMQ соединение закрыто")
                except Exception as e:
                    logger.warning(f"Ошибка при закрытии соединения: {e}")
                self._connection = None
