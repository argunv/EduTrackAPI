import json

from aio_pika import DeliveryMode, Message, connect_robust

from edutrack.config.settings import get_settings


class EmailPublisher:
    def __init__(self):
        self.settings = get_settings()

    async def publish_outbox(self, outbox_id: str) -> None:
        connection = await connect_robust(self.settings.rabbitmq_url)
        try:
            channel = await connection.channel()
            queue = await channel.declare_queue(self.settings.rabbitmq_email_queue, durable=True)
            payload = json.dumps({"outbox_id": outbox_id}).encode()
            await channel.default_exchange.publish(
                Message(payload, delivery_mode=DeliveryMode.PERSISTENT),
                routing_key=queue.name,
            )
        finally:
            await connection.close()
