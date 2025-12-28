"""Тесты для email сервисов и других модулей с низким покрытием."""
from datetime import UTC
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from edutrack.application.messages import MessageService
from edutrack.application.password_reset import PasswordResetService
from edutrack.infrastructure.email.sender import send_email
from edutrack.infrastructure.services.security import hash_password, verify_password
from helpers.assertions import assert_http_exception_async
from helpers.factories import (
    GradeFactory,
    LessonFactory,
    MessageFactory,
    UserFactory,
)
from helpers.mocks import DummySession, RepositoryMocks, SMTPMocks
from helpers.patches import patch_cache, patch_send_email, patch_smtp_settings


@pytest.mark.asyncio
async def test_password_reset_service_request_reset(monkeypatch):
    """Тест запроса восстановления пароля."""
    user = UserFactory.create_user(email="test@example.com")

    user_repo = RepositoryMocks.create_user_repo(users_by_email={"test@example.com": user})
    token_repo = RepositoryMocks.create_token_repo()

    session = DummySession()
    service = PasswordResetService(session)
    service.users = user_repo
    service.tokens = token_repo

    with patch_send_email():
        await service.request_reset("test@example.com")

    assert session.committed


@pytest.mark.asyncio
async def test_password_reset_service_request_reset_nonexistent_user(monkeypatch):
    """Тест запроса восстановления пароля для несуществующего пользователя."""
    user_repo = RepositoryMocks.create_user_repo(users_by_email={})

    session = DummySession()
    service = PasswordResetService(session)
    service.users = user_repo

    # Не должно быть ошибки, даже если пользователь не существует
    await service.request_reset("nonexistent@example.com")
    # Сессия не должна быть закоммичена, так как пользователь не найден
    assert not session.committed


@pytest.mark.asyncio
async def test_password_reset_service_reset_password(monkeypatch):
    """Тест сброса пароля по токену."""
    user = UserFactory.create_user(password_hash="old_hash")
    token = "valid_token"
    reset_token = SimpleNamespace(
        id=uuid4(),
        user_id=user.id,
        token=token,
        used=False,
        expires_at=None
    )

    token_repo = RepositoryMocks.create_token_repo(
        tokens_by_token={token: reset_token}
    )
    user_repo = RepositoryMocks.create_user_repo(users_by_id={user.id: user})

    session = DummySession()
    service = PasswordResetService(session)
    service.tokens = token_repo
    service.users = user_repo

    await service.reset_password(token, "new_password")
    assert session.committed
    assert user.password_hash != "old_hash"  # Пароль должен быть изменен
    # Проверяем, что токен помечен как использованный
    assert len(token_repo.mark_as_used_calls) == 1
    assert token_repo.mark_as_used_calls[0] == reset_token.id


@pytest.mark.asyncio
async def test_password_reset_service_reset_password_user_not_found(monkeypatch):
    """Тест сброса пароля, когда пользователь не найден."""
    token = "valid_token"
    user_id = uuid4()
    reset_token = SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        token=token,
        used=False,
        expires_at=None
    )

    token_repo = RepositoryMocks.create_token_repo(tokens_by_token={token: reset_token})
    user_repo = RepositoryMocks.create_user_repo(users_by_id={})

    session = DummySession()
    service = PasswordResetService(session)
    service.tokens = token_repo
    service.users = user_repo

    await assert_http_exception_async(
        service.reset_password(token, "new_password"),
        status_code=404,
        detail_contains="не найден"
    )


@pytest.mark.asyncio
async def test_password_reset_service_reset_password_invalid_token(monkeypatch):
    """Тест сброса пароля с недействительным токеном."""
    token_repo = RepositoryMocks.create_token_repo(tokens_by_token={})

    session = DummySession()
    service = PasswordResetService(session)
    service.tokens = token_repo

    await assert_http_exception_async(
        service.reset_password("invalid_token", "new_password"),
        status_code=400
    )


@pytest.mark.asyncio
async def test_security_hash_and_verify_password():
    """Тест хеширования и проверки паролей."""
    password = "test_password_123"
    hashed = hash_password(password)

    assert hashed != password
    assert len(hashed) > 20

    # Проверяем, что пароль правильно проверяется
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


@pytest.mark.asyncio
async def test_message_service_create_message(monkeypatch):
    """Тест создания сообщения."""
    sender_id = uuid4()
    message_repo = RepositoryMocks.create_message_repo()

    session = DummySession()
    service = MessageService(session)
    service.messages = message_repo
    service.outbox = MagicMock()
    service.publisher = MagicMock()

    message = await service.create_message(
        sender_id=sender_id,
        subject="Test",
        body="Test body",
        recipient_user_ids=[uuid4()]
    )

    assert message.id is not None
    assert session.committed


@pytest.mark.asyncio
async def test_message_service_enqueue_email(monkeypatch):
    """Тест добавления email в очередь."""
    message = MessageFactory.create_message(subject="Test", body="Body")
    outbox_id = uuid4()

    message_repo = RepositoryMocks.create_message_repo(
        messages_by_id={message.id: message}
    )

    class OutRepo:
        async def enqueue(self, message_id, recipients, subject, body):
            return type('obj', (object,), {
                'id': outbox_id,
                'status': type('obj', (object,), {'value': 'pending'})()
            })()

    class Pub:
        async def publish_outbox(self, outbox_id):
            pass

    session = DummySession()
    service = MessageService(session)
    service.messages = message_repo
    service.outbox = OutRepo()
    service.publisher = Pub()

    outbox = await service.enqueue_email(message.id, ["test@example.com"])

    assert outbox.id == outbox_id
    assert session.committed


@pytest.mark.asyncio
async def test_message_service_enqueue_email_not_found(monkeypatch):
    """Тест добавления email в очередь для несуществующего сообщения."""
    message_repo = RepositoryMocks.create_message_repo(messages_by_id={})

    session = DummySession()
    service = MessageService(session)
    service.messages = message_repo

    await assert_http_exception_async(
        service.enqueue_email(uuid4(), ["test@example.com"]),
        status_code=404
    )


@pytest.mark.asyncio
async def test_send_email_success(monkeypatch):
    """Тест успешной отправки email."""
    mock_smtp = SMTPMocks.create_smtp_mock(port=587, supports_starttls=True)

    with patch("edutrack.infrastructure.email.sender.SMTP", return_value=mock_smtp):
        with patch_smtp_settings(port=587, use_tls=True):
            await send_email(["recipient@example.com"], "Subject", "Body")

    mock_smtp.connect.assert_called_once()
    mock_smtp.send_message.assert_called_once()
    mock_smtp.quit.assert_called_once()


@pytest.mark.asyncio
async def test_send_email_port_465(monkeypatch):
    """Тест отправки email через порт 465 (SSL/TLS)."""
    mock_smtp = SMTPMocks.create_smtp_mock(port=465, supports_starttls=False)

    with patch("edutrack.infrastructure.email.sender.SMTP", return_value=mock_smtp):
        with patch_smtp_settings(port=465, use_tls=True):
            await send_email(["recipient@example.com"], "Subject", "Body")

    mock_smtp.connect.assert_called_once()
    mock_smtp.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_send_email_multiple_recipients(monkeypatch):
    """Тест отправки email нескольким получателям."""
    mock_smtp = SMTPMocks.create_smtp_mock(port=587, supports_starttls=True)

    with patch("edutrack.infrastructure.email.sender.SMTP", return_value=mock_smtp):
        with patch_smtp_settings(port=587, use_tls=True):
            recipients = ["user1@example.com", "user2@example.com", "user3@example.com"]
            await send_email(recipients, "Subject", "Body")

    # Проверяем, что все получатели были добавлены
    call_args = mock_smtp.send_message.call_args[0][0]
    assert "user1@example.com" in call_args["To"]
    assert "user2@example.com" in call_args["To"]
    assert "user3@example.com" in call_args["To"]


@pytest.mark.asyncio
async def test_performance_service_get_performance(monkeypatch):
    """Тест получения успеваемости студента."""
    from datetime import datetime

    from edutrack.application.performance import PerformanceService

    student_id = uuid4()
    subject_id = uuid4()

    # Мокаем результат запроса
    grade = GradeFactory.create_grade(
        value=5,
        created_at=datetime(2024, 1, 15, tzinfo=UTC)
    )
    lesson = LessonFactory.create_lesson(subject_id=subject_id)
    subject = type('obj', (object,), {'id': subject_id, 'name': 'Math'})()

    mock_result = MagicMock()
    mock_result.all.return_value = [(grade, lesson, subject)]

    session = DummySession()
    session.execute = AsyncMock(return_value=mock_result)

    service = PerformanceService(session)
    result = await service.get_performance(student_id, month=1, year=2024)

    assert len(result) == 1
    assert result[0]["subject_name"] == "Math"
    assert result[0]["average_grade"] == 5.0
    assert result[0]["grade_count"] == 1


@pytest.mark.asyncio
async def test_performance_service_invalid_month(monkeypatch):
    """Тест получения успеваемости с невалидным месяцем."""
    from edutrack.application.performance import PerformanceService

    session = DummySession()
    service = PerformanceService(session)

    with pytest.raises(ValueError, match="Месяц должен быть от 1 до 12"):
        await service.get_performance(uuid4(), month=0, year=2024)

    with pytest.raises(ValueError, match="Месяц должен быть от 1 до 12"):
        await service.get_performance(uuid4(), month=13, year=2024)


@pytest.mark.asyncio
async def test_performance_service_no_grades(monkeypatch):
    """Тест получения успеваемости без оценок."""
    from edutrack.application.performance import PerformanceService

    student_id = uuid4()

    mock_result = MagicMock()
    mock_result.all.return_value = []

    session = DummySession()
    session.execute = AsyncMock(return_value=mock_result)

    service = PerformanceService(session)
    result = await service.get_performance(student_id, month=1, year=2024)

    assert result == []


@pytest.mark.asyncio
async def test_classmates_service_get_classmates(monkeypatch):
    """Тест получения одноклассников."""
    from edutrack.application.classmates import ClassmatesService

    student_id = uuid4()
    class_id = uuid4()
    classmate_id = uuid4()

    student = SimpleNamespace(id=student_id)
    classmate = SimpleNamespace(id=classmate_id)

    class StudentRepo:
        async def get(self, sid):
            return student

    # Мокаем scalars для получения class_ids
    mock_class_ids = MagicMock()
    mock_class_ids.all.return_value = [class_id]

    # Мокаем scalars для получения одноклассников
    mock_classmates = MagicMock()
    mock_classmates.unique.return_value.all.return_value = [classmate]

    session = DummySession()
    session.scalars = AsyncMock(side_effect=[mock_class_ids, mock_classmates])

    service = ClassmatesService(session)
    service.students = StudentRepo()

    result = await service.get_classmates(student_id)

    assert len(result) == 1
    assert result[0].id == classmate_id


@pytest.mark.asyncio
async def test_classmates_service_no_student(monkeypatch):
    """Тест получения одноклассников для несуществующего студента."""
    from edutrack.application.classmates import ClassmatesService

    class StudentRepo:
        async def get(self, sid):
            return None

    session = DummySession()
    service = ClassmatesService(session)
    service.students = StudentRepo()

    result = await service.get_classmates(uuid4())

    assert result == []


@pytest.mark.asyncio
async def test_classmates_service_no_classes(monkeypatch):
    """Тест получения одноклассников для студента без классов."""
    from edutrack.application.classmates import ClassmatesService

    student_id = uuid4()
    student = SimpleNamespace(id=student_id)

    class StudentRepo:
        async def get(self, sid):
            return student

    mock_class_ids = MagicMock()
    mock_class_ids.all.return_value = []

    session = DummySession()
    session.scalars = AsyncMock(return_value=mock_class_ids)

    service = ClassmatesService(session)
    service.students = StudentRepo()

    result = await service.get_classmates(student_id)

    assert result == []


@pytest.mark.asyncio
async def test_lesson_service_create_lesson(monkeypatch):
    """Тест создания урока."""
    from edutrack.application.lessons import LessonService

    lesson = LessonFactory.create_lesson(topic="Test Topic")

    class LessonRepo:
        async def create_lesson(self, **kwargs):
            return lesson

    session = DummySession()
    service = LessonService(session)
    service.repo = LessonRepo()

    with patch_cache():
        result = await service.create_lesson(
            class_id=lesson.class_id,
            subject_id=lesson.subject_id,
            teacher_id=lesson.teacher_id,
            topic=lesson.topic,
            start_at=lesson.start_at,
            end_at=lesson.end_at
        )

    assert result.id == lesson.id
    assert session.committed


@pytest.mark.asyncio
async def test_lesson_service_list_schedule_cache_hit(monkeypatch):
    """Тест получения расписания из кэша."""
    from edutrack.application.lessons import LessonService

    class_id = uuid4()
    cached_data = [{"id": str(uuid4()), "topic": "Cached Lesson"}]

    session = DummySession()
    service = LessonService(session)

    with patch_cache(cache_hit=True, cache_data=cached_data):
        result = await service.list_schedule(class_id)

    assert result == cached_data


@pytest.mark.asyncio
async def test_lesson_service_list_schedule_cache_miss(monkeypatch):
    """Тест получения расписания без кэша."""
    from edutrack.application.lessons import LessonService

    class_id = uuid4()
    lesson = LessonFactory.create_lesson(topic="Test Lesson")

    class LessonRepo:
        async def list_for_class(self, cid):
            return [lesson]

    session = DummySession()
    service = LessonService(session)
    service.repo = LessonRepo()

    with patch_cache(cache_hit=False):
        result = await service.list_schedule(class_id)

    assert len(result) == 1
    assert result[0]["topic"] == "Test Lesson"
    assert result[0]["id"] == str(lesson.id)


@pytest.mark.asyncio
async def test_security_create_access_token(monkeypatch):
    """Тест создания JWT токена."""
    from datetime import datetime, timedelta

    from jose import jwt

    # Мокаем get_settings
    mock_settings_obj = MagicMock()
    mock_settings_obj.jwt_secret = "test_secret"
    mock_settings_obj.jwt_algorithm = "HS256"
    mock_settings_obj.jwt_exp_minutes = 30

    # Мокаем settings в модуле security
    with patch("edutrack.infrastructure.services.security.settings", mock_settings_obj):
        from edutrack.infrastructure.services.security import create_access_token

        user_id = "test_user_id"
        token = create_access_token(user_id)

        assert isinstance(token, str)
        assert len(token) > 0

        # Проверяем, что токен можно декодировать
        payload = jwt.decode(token, "test_secret", algorithms=["HS256"])
        assert payload["sub"] == user_id
        assert "exp" in payload

        # Проверяем, что срок действия примерно 30 минут
        exp_time = datetime.fromtimestamp(payload["exp"], tz=UTC)
        now = datetime.now(UTC)
        expected_exp = now + timedelta(minutes=30)
        # Допускаем разницу в 5 секунд (время выполнения теста)
        assert abs((exp_time - expected_exp).total_seconds()) < 5

