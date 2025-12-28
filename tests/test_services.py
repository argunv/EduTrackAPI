from datetime import UTC
from types import SimpleNamespace
from uuid import uuid4

import pytest
from edutrack.application.auth import AuthService
from edutrack.application.grades import GradeService
from edutrack.application.messages import MessageService
from edutrack.application.schools import SchoolService
from helpers.mocks import DummySession
from helpers.patches import patch_cache


@pytest.mark.asyncio
async def test_auth_service_success(monkeypatch):
    # Mock verify_password to avoid bcrypt initialization issues in tests
    def mock_verify_password(plain: str, hashed: str) -> bool:
        return plain == "secret" and hashed == "hashed_secret"

    user = SimpleNamespace(id=uuid4(), password_hash="hashed_secret")

    class Repo:
        async def get_by_email(self, email):
            return user

    monkeypatch.setattr(
        "edutrack.application.auth.verify_password", mock_verify_password
    )

    service = AuthService(session=None)  # type: ignore
    service.users = Repo()  # type: ignore
    token = await service.authenticate(email="user@example.com", password="secret")
    assert isinstance(token, str) and len(token) > 10


@pytest.mark.asyncio
async def test_auth_service_invalid_password(monkeypatch):
    """Тест аутентификации с неправильным паролем."""
    def mock_verify_password(plain: str, hashed: str) -> bool:
        return plain == "secret" and hashed == "hashed_secret"

    user = SimpleNamespace(id=uuid4(), password_hash="hashed_secret")

    class Repo:
        async def get_by_email(self, email):
            return user

    monkeypatch.setattr(
        "edutrack.application.auth.verify_password", mock_verify_password
    )

    service = AuthService(session=None)  # type: ignore
    service.users = Repo()  # type: ignore

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await service.authenticate(email="user@example.com", password="wrong_password")

    assert exc_info.value.status_code == 401
    assert "credentials" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_auth_service_user_not_found(monkeypatch):
    """Тест аутентификации несуществующего пользователя."""
    def mock_verify_password(plain: str, hashed: str) -> bool:
        return False

    class Repo:
        async def get_by_email(self, email):
            return None

    monkeypatch.setattr(
        "edutrack.application.auth.verify_password", mock_verify_password
    )

    service = AuthService(session=None)  # type: ignore
    service.users = Repo()  # type: ignore

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await service.authenticate(email="nonexistent@example.com", password="secret")

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_grade_service_cache(monkeypatch):
    student_id = uuid4()
    cached_payload = [{"id": "1"}]

    class Repo:
        async def list_for_student(self, sid):
            return []

    session = DummySession()
    service = GradeService(session=session)  # type: ignore
    service.repo = Repo()  # type: ignore

    # Используем патч кэша с cache_hit=True
    async def fake_set_cache(key, value, ttl_seconds):
        raise AssertionError("set_cache should not be called when cache hit")

    with patch_cache(cache_hit=True, cache_data=cached_payload):
        monkeypatch.setattr("edutrack.application.grades.set_cache", fake_set_cache)
        result = await service.list_grades(student_id)

    assert result == cached_payload


@pytest.mark.asyncio
async def test_message_service_enqueue(monkeypatch):
    msg_id = uuid4()
    outbox_id = uuid4()

    class MsgRepo:
        async def create_message(self, *args, **kwargs):
            return None

        async def add_recipients(self, *args, **kwargs):
            return None

        async def get(self, mid):
            return SimpleNamespace(id=msg_id, subject="Hello", body="World")

    class OutRepo:
        async def enqueue(self, **kwargs):
            return SimpleNamespace(id=outbox_id, status=SimpleNamespace(value="pending"))

    class Pub:
        def __init__(self):
            self.called = False
            self.last = None

        async def publish_outbox(self, oid):
            self.called = True
            self.last = oid

    session = DummySession()
    service = MessageService(session=session)  # type: ignore
    service.messages = MsgRepo()  # type: ignore
    service.outbox = OutRepo()  # type: ignore
    publisher = Pub()
    service.publisher = publisher  # type: ignore

    outbox = await service.enqueue_email(message_id=msg_id, recipients_emails=["a@b.com"])
    assert outbox.id == outbox_id
    assert publisher.called and publisher.last == str(outbox_id)


@pytest.mark.asyncio
async def test_school_service_caching(monkeypatch):
    session = DummySession()

    class Repo:
        async def create_school(self, name, address):
            return SimpleNamespace(id=uuid4(), name=name, address=address)

        async def list_schools(self):
            return [SimpleNamespace(id=uuid4(), name="S1", address=None)]

    service = SchoolService(session=session)  # type: ignore
    service.repo = Repo()  # type: ignore

    with patch_cache(cache_hit=False) as cache_mocks:
        await service.create_school("S1", None)
        assert len(cache_mocks["invalidate_calls"]) == 1
        assert session.committed is True
        schools = await service.list_schools()
        assert len(schools) == 1


@pytest.mark.asyncio
async def test_grade_service_cache_miss(monkeypatch):
    """Тест GradeService при отсутствии кэша."""
    from datetime import datetime

    from helpers.factories import GradeFactory

    student_id = uuid4()
    grade = GradeFactory.create_grade(
        student_id=student_id,
        value=5,
        comment="Отлично",
        created_at=datetime.now(UTC)
    )

    class Repo:
        async def list_for_student(self, sid):
            return [grade]

    session = DummySession()
    service = GradeService(session=session)  # type: ignore
    service.repo = Repo()  # type: ignore

    with patch_cache(cache_hit=False) as cache_mocks:
        result = await service.list_grades(student_id)

    # Проверяем, что данные получены из репозитория
    assert len(result) == 1
    assert result[0]["id"] == str(grade.id)
    assert result[0]["value"] == 5
    assert result[0]["comment"] == "Отлично"

    # Проверяем, что данные сохранены в кэш
    assert len(cache_mocks["set_calls"]) == 1
    assert cache_mocks["set_calls"][0]["key"] == f"cache:grades:{student_id}"
    assert cache_mocks["set_calls"][0]["ttl"] == 60  # GRADES_TTL
