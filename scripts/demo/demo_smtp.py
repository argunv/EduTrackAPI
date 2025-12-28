#!/usr/bin/env python3
"""Комплексный скрипт для тестирования всех email сервисов EduTrack API.

Этот скрипт работает с локальными сервисами (не в Docker):
- База данных: localhost:5432
- RabbitMQ: localhost:5672

Требования:
- PostgreSQL должен быть запущен локально на порту 5432
- RabbitMQ должен быть запущен локально на порту 5672
- База данных должна быть создана и миграции применены
- Переменные окружения должны быть настроены в .env файле
"""

import asyncio
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from edutrack.application.password_reset import PasswordResetService
from edutrack.config.settings import Settings
from edutrack.infrastructure.db.models import EmailOutbox, Message, MessageDeliveryStatus, User
from edutrack.infrastructure.repositories.sqlalchemy import (
    SqlAlchemyUserRepository,
    SqlAlchemyMessageRepository,
    SqlAlchemyEmailOutboxRepository,
)
from edutrack.infrastructure.services.security import hash_password
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import json
from aio_pika import DeliveryMode, Message as RabbitMQMessage, connect_robust


def get_local_database_url() -> str:
    """Получает URL базы данных для локального подключения."""
    settings = Settings()
    # Преобразуем Docker хосты в localhost
    url = settings.database_url.replace("@postgres:", "@localhost:")
    url = url.replace("postgres:5432", "localhost:5432")
    return url


def get_local_rabbitmq_url() -> str:
    """Получает URL RabbitMQ для локального подключения."""
    settings = Settings()
    # Преобразуем Docker хосты в localhost
    url = settings.rabbitmq_url.replace("@rabbitmq:", "@localhost:")
    url = url.replace("rabbitmq:5672", "localhost:5672")
    return url


# Создаем локальный engine и sessionmaker для работы с локальной БД
_local_db_url = get_local_database_url()
_local_engine = create_async_engine(_local_db_url, echo=False, future=True)
LocalSessionLocal = async_sessionmaker(_local_engine, expire_on_commit=False, autoflush=False, autocommit=False, class_=AsyncSession)


class LocalEmailPublisher:
    """Локальная версия EmailPublisher для работы с локальным RabbitMQ."""
    
    def __init__(self):
        self.rabbitmq_url = get_local_rabbitmq_url()
        settings = Settings()
        self.queue_name = settings.rabbitmq_email_queue
    
    async def publish_outbox(self, outbox_id: str) -> None:
        """Публикует сообщение в локальную очередь RabbitMQ."""
        connection = await connect_robust(self.rabbitmq_url)
        try:
            channel = await connection.channel()
            queue = await channel.declare_queue(self.queue_name, durable=True)
            payload = json.dumps({"outbox_id": outbox_id}).encode()
            await channel.default_exchange.publish(
                RabbitMQMessage(payload, delivery_mode=DeliveryMode.PERSISTENT),
                routing_key=queue.name,
            )
        finally:
            await connection.close()


class LocalMessageService:
    """Локальная версия MessageService для работы с локальной БД и RabbitMQ."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.messages = SqlAlchemyMessageRepository(session)
        self.outbox = SqlAlchemyEmailOutboxRepository(session)
        self.publisher = LocalEmailPublisher()
    
    async def create_message(self, sender_id: UUID, subject: str, body: str, recipient_user_ids: list[UUID]):
        """Создает сообщение."""
        message = await self.messages.create_message(sender_id=sender_id, subject=subject, body=body)
        if recipient_user_ids:
            await self.messages.add_recipients(message_id=message.id, recipients=recipient_user_ids)
        await self.session.commit()
        return message
    
    async def enqueue_email(self, message_id: UUID, recipients_emails: Sequence[str]):
        """Добавляет email в очередь отправки."""
        message = await self.messages.get(message_id)
        if not message:
            raise ValueError(f"Message {message_id} not found")
        outbox_entry = await self.outbox.enqueue(
            message_id=message_id,
            recipients=list(recipients_emails),
            subject=message.subject,
            body=message.body,
        )
        await self.session.commit()
        await self.publisher.publish_outbox(str(outbox_entry.id))
        return outbox_entry


def print_section(title: str):
    """Печатает заголовок секции."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_step(step_num: int, title: str):
    """Печатает заголовок шага."""
    print(f"\n📋 Шаг {step_num}: {title}")
    print("-" * 70)


async def ensure_users_exist():
    """Убеждается, что все необходимые пользователи существуют."""
    print_step(0, "Проверка и создание тестовых пользователей")
    
    users_to_create = [
        {"email": "vladislavargun200710@gmail.com", "full_name": "Vladislav Argun", "password": "demo123"},
        {"email": "v_argun@inbox.ru", "full_name": "Vladislav Argun", "password": "demo123"},
        {"email": "teacher1@demo.com", "full_name": "Анна Смирнова", "password": "demo123"},
        {"email": "parent1@demo.com", "full_name": "Ольга Иванова", "password": "demo123"},
    ]
    
    async with LocalSessionLocal() as session:
        repo = SqlAlchemyUserRepository(session)
        
        for user_data in users_to_create:
            existing = await repo.get_by_email(user_data["email"])
            if existing:
                print(f"  ✓ Пользователь {user_data['email']} уже существует")
            else:
                user = await repo.create_user(
                    email=user_data["email"],
                    full_name=user_data["full_name"],
                    password_hash=hash_password(user_data["password"]),
                    roles=["student"] if "student" in user_data["email"] or "@gmail" in user_data["email"] or "@inbox" in user_data["email"] else ["teacher"] if "teacher" in user_data["email"] else ["guardian"],
                )
                await session.commit()
                print(f"  ✓ Создан пользователь: {user_data['email']}")


async def get_user_by_email(email: str, session: AsyncSession | None = None) -> User | None:
    """Получает пользователя по email."""
    if session is not None:
        repo = SqlAlchemyUserRepository(session)
        return await repo.get_by_email(email)
    else:
        async with LocalSessionLocal() as sess:
            repo = SqlAlchemyUserRepository(sess)
            return await repo.get_by_email(email)


async def get_all_users(session: AsyncSession | None = None) -> list[User]:
    """Получает список всех пользователей."""
    if session is not None:
        stmt = select(User)
        result = await session.scalars(stmt)
        return list(result.all())
    else:
        async with LocalSessionLocal() as sess:
            stmt = select(User)
            result = await sess.scalars(stmt)
            return list(result.all())


async def check_outbox_status(outbox_id: UUID) -> EmailOutbox | None:
    """Проверяет статус записи в outbox."""
    async with LocalSessionLocal() as session:
        stmt = select(EmailOutbox).where(EmailOutbox.id == outbox_id)
        return await session.scalar(stmt)


async def test_1_single_recipient_email():
    """Тест 1: Отправка email одному получателю."""
    print_step(1, "Отправка email одному получателю")
    
    async with LocalSessionLocal() as session:
        # Получаем отправителя (админ) и получателя
        repo = SqlAlchemyUserRepository(session)
        admin = await repo.get_by_email("admin@test.com")
        recipient = await repo.get_by_email("student1@demo.com")
        
        if not admin or not recipient:
            print("  ❌ Не найдены необходимые пользователи")
            return
        
        service = LocalMessageService(session)
        
        # Создаем сообщение
        message = await service.create_message(
            sender_id=admin.id,
            subject="Тестовое сообщение для одного получателя",
            body="Это тестовое сообщение отправляется одному получателю для проверки работы email сервиса.",
            recipient_user_ids=[recipient.id],
        )
        print(f"  ✓ Сообщение создано (ID: {message.id})")
        
        # Отправляем email
        outbox = await service.enqueue_email(
            message_id=message.id,
            recipients_emails=[recipient.email],
        )
        print(f"  ✓ Email добавлен в очередь (Outbox ID: {outbox.id})")
        print(f"  ✓ Статус: {outbox.status.value}")
        print(f"  ✓ Получатель: {recipient.email}")


async def test_2_multiple_recipients_email():
    """Тест 2: Отправка email нескольким получателям."""
    print_step(2, "Отправка email нескольким получателям")
    
    async with LocalSessionLocal() as session:
        repo = SqlAlchemyUserRepository(session)
        admin = await repo.get_by_email("admin@test.com")
        recipients = [
            await repo.get_by_email("student1@demo.com"),
            await repo.get_by_email("student2@demo.com"),
            await repo.get_by_email("student3@demo.com"),
        ]
        recipients = [r for r in recipients if r is not None]
        
        if not admin or not recipients:
            print("  ❌ Не найдены необходимые пользователи")
            return
        
        service = LocalMessageService(session)
        
        # Создаем сообщение
        message = await service.create_message(
            sender_id=admin.id,
            subject="Тестовое сообщение для нескольких получателей",
            body="Это тестовое сообщение отправляется нескольким получателям одновременно.",
            recipient_user_ids=[r.id for r in recipients],
        )
        print(f"  ✓ Сообщение создано (ID: {message.id})")
        print(f"  ✓ Количество получателей в системе: {len(recipients)}")
        
        # Отправляем email
        recipient_emails = [r.email for r in recipients]
        outbox = await service.enqueue_email(
            message_id=message.id,
            recipients_emails=recipient_emails,
        )
        print(f"  ✓ Email добавлен в очередь (Outbox ID: {outbox.id})")
        print(f"  ✓ Статус: {outbox.status.value}")
        print(f"  ✓ Получатели: {', '.join(recipient_emails)}")


async def test_3_broadcast_email():
    """Тест 3: Массовая рассылка всем пользователям."""
    print_step(3, "Массовая рассылка всем пользователям")
    
    async with LocalSessionLocal() as session:
        repo = SqlAlchemyUserRepository(session)
        admin = await repo.get_by_email("admin@test.com")
        stmt = select(User)
        result = await session.scalars(stmt)
        users = list(result.all())
        
        if not admin or not users:
            print("  ❌ Не найдены необходимые пользователи")
            return
        
        service = LocalMessageService(session)
        
        # Создаем сообщение
        message = await service.create_message(
            sender_id=admin.id,
            subject="Массовая рассылка: Добро пожаловать в EduTrack!",
            body="""Здравствуйте!

Это массовая рассылка всем пользователям системы EduTrack.

Система успешно настроена и готова к работе!

С уважением,
Команда EduTrack""",
            recipient_user_ids=[user.id for user in users],
        )
        print(f"  ✓ Сообщение создано (ID: {message.id})")
        print(f"  ✓ Всего пользователей в системе: {len(users)}")
        
        # Отправляем email всем пользователям
        recipient_emails = [user.email for user in users]
        outbox = await service.enqueue_email(
            message_id=message.id,
            recipients_emails=recipient_emails,
        )
        print(f"  ✓ Email добавлен в очередь (Outbox ID: {outbox.id})")
        print(f"  ✓ Статус: {outbox.status.value}")
        print(f"  ✓ Количество получателей: {len(recipient_emails)}")


async def test_4_message_without_recipients():
    """Тест 4: Создание сообщения без получателей, затем отправка по email."""
    print_step(4, "Создание сообщения без получателей, затем отправка по email")
    
    async with LocalSessionLocal() as session:
        repo = SqlAlchemyUserRepository(session)
        admin = await repo.get_by_email("admin@test.com")
        
        if not admin:
            print("  ❌ Администратор не найден")
            return
        
        service = LocalMessageService(session)
        
        # Создаем сообщение без получателей
        message = await service.create_message(
            sender_id=admin.id,
            subject="Сообщение без получателей в системе",
            body="Это сообщение создано без получателей в системе, но будет отправлено по email адресам.",
            recipient_user_ids=[],
        )
        print(f"  ✓ Сообщение создано без получателей (ID: {message.id})")
        
        # Отправляем email по внешним адресам
        external_emails = ["vladislavargun200710@gmail.com", "v_argun@inbox.ru"]
        outbox = await service.enqueue_email(
            message_id=message.id,
            recipients_emails=external_emails,
        )
        print(f"  ✓ Email добавлен в очередь (Outbox ID: {outbox.id})")
        print(f"  ✓ Статус: {outbox.status.value}")
        print(f"  ✓ Внешние получатели: {', '.join(external_emails)}")


async def test_5_password_reset_email():
    """Тест 5: Отправка email для восстановления пароля."""
    print_step(5, "Отправка email для восстановления пароля")
    
    try:
        async with LocalSessionLocal() as session:
            service = PasswordResetService(session)
            
            # Запрашиваем восстановление пароля для существующего пользователя
            test_email = "v_argun@inbox.ru"
            print(f"  📧 Запрос восстановления пароля для: {test_email}")
            
            try:
                await service.request_reset(email=test_email)
                print(f"  ✓ Запрос на восстановление пароля обработан")
                print(f"  💡 Email отправлен напрямую (не через outbox)")
                print(f"  ⚠ Если письмо не пришло, проверьте:")
                print(f"     - Настройки SMTP в .env файле")
                print(f"     - Логи приложения на наличие ошибок SMTP")
                print(f"     - Доступность SMTP сервера")
            except Exception as e:
                print(f"  ❌ Ошибка при отправке email: {e}")
                print(f"  💡 Проверьте настройки SMTP в .env файле")
    except Exception as e:
        print(f"  ⚠ Ошибка при восстановлении пароля: {e}")
        print(f"  💡 Это может произойти, если токен уже существует (нормально для повторных запусков)")


async def test_6_password_reset_nonexistent_user():
    """Тест 6: Попытка восстановления пароля для несуществующего пользователя."""
    print_step(6, "Попытка восстановления пароля для несуществующего пользователя")
    
    async with LocalSessionLocal() as session:
        service = PasswordResetService(session)
        
        # Запрашиваем восстановление пароля для несуществующего пользователя
        nonexistent_email = "nonexistent@example.com"
        print(f"  📧 Запрос восстановления пароля для: {nonexistent_email}")
        await service.request_reset(email=nonexistent_email)
        print(f"  ✓ Запрос обработан (без ошибок, но email не отправлен)")
        print(f"  💡 Система не раскрывает, существует ли пользователь")


async def test_10_password_reset_confirm():
    """Тест 10: Подтверждение восстановления пароля по токену."""
    print_step(10, "Подтверждение восстановления пароля по токену")
    
    async with LocalSessionLocal() as session:
        service = PasswordResetService(session)
        
        # Сначала создаем токен для тестирования
        test_email = "v_argun@inbox.ru"
        repo = SqlAlchemyUserRepository(session)
        user = await repo.get_by_email(test_email)
        
        if not user:
            print(f"  ❌ Пользователь {test_email} не найден")
            return
        
        # Запрашиваем восстановление пароля
        print(f"  📧 Создаем токен для: {test_email}")
        await service.request_reset(email=test_email)
        
        # Получаем токен из базы
        from edutrack.infrastructure.repositories.sqlalchemy import SqlAlchemyPasswordResetTokenRepository
        token_repo = SqlAlchemyPasswordResetTokenRepository(session)
        from sqlalchemy import select
        from edutrack.infrastructure.db.models import PasswordResetToken
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used == False
        ).order_by(PasswordResetToken.created_at.desc())
        token_obj = await session.scalar(stmt)
        
        if not token_obj:
            print(f"  ❌ Токен не найден")
            return
        
        print(f"  ✓ Токен найден: {token_obj.token[:20]}...")
        print(f"  💡 Для тестирования используйте этот токен или токен из письма")
        print(f"  💡 Пример использования через API:")
        print(f"     curl -X POST http://127.0.0.1:8000/api/v1/auth/password-reset/confirm \\")
        print(f"       -H 'Content-Type: application/json' \\")
        print(f"       -d '{{\"token\": \"{token_obj.token}\", \"new_password\": \"newpassword123\"}}'")
        
        # Тестируем восстановление пароля
        new_password = "newpassword123"
        print(f"\n  🔄 Тестируем восстановление пароля...")
        try:
            await service.reset_password(token=token_obj.token, new_password=new_password)
            print(f"  ✓ Пароль успешно изменен!")
            print(f"  💡 Новый пароль: {new_password}")
            print(f"  💡 Теперь можно войти с новым паролем")
        except Exception as e:
            print(f"  ❌ Ошибка при восстановлении пароля: {e}")


async def test_7_check_outbox_statuses():
    """Тест 7: Проверка статусов записей в outbox."""
    print_step(7, "Проверка статусов записей в outbox")
    
    async with LocalSessionLocal() as session:
        # Получаем все записи из outbox
        stmt = select(EmailOutbox).order_by(EmailOutbox.created_at.desc()).limit(10)
        result = await session.scalars(stmt)
        outbox_entries = list(result.all())
        
        print(f"  📊 Найдено записей в outbox: {len(outbox_entries)}")
        
        status_counts = {}
        for entry in outbox_entries:
            status = entry.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"\n  Статистика по статусам:")
        for status, count in status_counts.items():
            print(f"    - {status}: {count}")
        
        # Показываем последние записи
        print(f"\n  Последние записи:")
        for entry in outbox_entries[:5]:
            print(f"    - ID: {entry.id}")
            print(f"      Статус: {entry.status.value}")
            print(f"      Получателей: {len(entry.recipients)}")
            print(f"      Тема: {entry.subject[:50]}...")
            if entry.last_error:
                print(f"      Ошибка: {entry.last_error[:100]}...")
            print()


async def test_8_multiple_messages_same_recipient():
    """Тест 8: Отправка нескольких сообщений одному получателю."""
    print_step(8, "Отправка нескольких сообщений одному получателю")
    
    async with LocalSessionLocal() as session:
        repo = SqlAlchemyUserRepository(session)
        admin = await repo.get_by_email("admin@test.com")
        recipient = await repo.get_by_email("student1@demo.com")
        
        if not admin or not recipient:
            print("  ❌ Не найдены необходимые пользователи")
            if not admin:
                print("     - Администратор (admin@test.com) не найден")
            if not recipient:
                print("     - Получатель (student1@demo.com) не найден")
            return
        
        service = LocalMessageService(session)
        
        messages_data = [
            {
                "subject": "Первое сообщение",
                "body": "Это первое сообщение в серии тестовых сообщений.",
            },
            {
                "subject": "Второе сообщение",
                "body": "Это второе сообщение в серии тестовых сообщений.",
            },
            {
                "subject": "Третье сообщение",
                "body": "Это третье сообщение в серии тестовых сообщений.",
            },
        ]
        
        outbox_ids = []
        for msg_data in messages_data:
            message = await service.create_message(
                sender_id=admin.id,
                subject=msg_data["subject"],
                body=msg_data["body"],
                recipient_user_ids=[recipient.id],
            )
            
            outbox = await service.enqueue_email(
                message_id=message.id,
                recipients_emails=[recipient.email],
            )
            outbox_ids.append(outbox.id)
            print(f"  ✓ Сообщение '{msg_data['subject']}' добавлено в очередь (Outbox ID: {outbox.id})")
        
        print(f"\n  ✓ Всего отправлено сообщений: {len(outbox_ids)}")


async def test_9_wait_and_check_delivery():
    """Тест 9: Ожидание и проверка доставки email."""
    print_step(9, "Ожидание и проверка доставки email")
    
    print("  ⏳ Ожидание обработки очереди (10 секунд)...")
    await asyncio.sleep(10)
    
    async with LocalSessionLocal() as session:
        # Получаем последние записи
        stmt = select(EmailOutbox).order_by(EmailOutbox.created_at.desc()).limit(5)
        result = await session.scalars(stmt)
        outbox_entries = list(result.all())
        
        print(f"\n  📊 Проверка статусов последних {len(outbox_entries)} записей:")
        
        for entry in outbox_entries:
            status_icon = "✓" if entry.status == MessageDeliveryStatus.sent else "⏳" if entry.status == MessageDeliveryStatus.pending else "❌"
            print(f"    {status_icon} Outbox ID: {entry.id}")
            print(f"       Статус: {entry.status.value}")
            print(f"       Получателей: {len(entry.recipients)}")
            if entry.sent_at:
                print(f"       Отправлено: {entry.sent_at}")
            if entry.last_error:
                print(f"       Ошибка: {entry.last_error[:100]}")
            print()


async def main():
    """Главная функция для запуска всех тестов."""
    print_section("Комплексное тестирование Email сервисов EduTrack API")
    
    try:
        # Подготовка
        await ensure_users_exist()
        
        # Тесты отправки email через outbox
        await test_1_single_recipient_email()
        await asyncio.sleep(1)  # Небольшая задержка между тестами
        
        await test_2_multiple_recipients_email()
        await asyncio.sleep(1)
        
        await test_3_broadcast_email()
        await asyncio.sleep(1)
        
        await test_4_message_without_recipients()
        await asyncio.sleep(1)
        
        # Тесты восстановления пароля
        await test_5_password_reset_email()
        await asyncio.sleep(1)
        
        await test_6_password_reset_nonexistent_user()
        await asyncio.sleep(1)
        
        # Проверка статусов
        await test_7_check_outbox_statuses()
        await asyncio.sleep(1)
        
        # Дополнительные тесты
        await test_8_multiple_messages_same_recipient()
        await asyncio.sleep(1)
        
        # Финальная проверка доставки
        await test_9_wait_and_check_delivery()
        await asyncio.sleep(1)
        
        # Тест подтверждения восстановления пароля
        await test_10_password_reset_confirm()
        
        print_section("✅ Все тесты завершены!")
        print("\n💡 Рекомендации:")
        print("   - Скрипт работает с локальными сервисами (localhost)")
        print("   - Проверьте логи notifier (если запущен локально)")
        print("   - Проверьте почтовые ящики получателей")
        print("   - Проверьте статусы в таблице email_outbox:")
        print("     psql -U edutrack -d edutrack -c \"SELECT id, status, recipients, subject, created_at, sent_at FROM email_outbox ORDER BY created_at DESC LIMIT 10;\"")
        print("\n📝 Примечание:")
        print("   - Для обработки очереди RabbitMQ запустите notifier локально:")
        print("     python -m edutrack.notifier.main")
        
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении тестов: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

