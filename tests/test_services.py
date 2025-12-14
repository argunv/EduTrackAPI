import pytest
from types import SimpleNamespace
from uuid import uuid4

from edutrack.application.auth import AuthService
from edutrack.infrastructure.services.security import hash_password
from edutrack.application.grades import GradeService
from edutrack.application.messages import MessageService
from edutrack.application.schools import SchoolService


class DummySession:
    def __init__(self):
        self.committed = False

    async def commit(self):
        self.committed = True

    async def execute(self, *args, **kwargs):
        return None


@pytest.mark.asyncio
async def test_auth_service_success(monkeypatch):
    user = SimpleNamespace(id=uuid4(), password_hash=hash_password("secret"))

    class Repo:
        async def get_by_email(self, email):
            return user

    service = AuthService(session=None)  # type: ignore
    service.users = Repo()  # type: ignore
    token = await service.authenticate(email="user@example.com", password="secret")
    assert isinstance(token, str) and len(token) > 10


@pytest.mark.asyncio
async def test_grade_service_cache(monkeypatch):
    student_id = uuid4()
    cached_payload = [{"id": "1"}]

    async def fake_get_cache(key):
        return cached_payload

    async def fake_set_cache(key, value, ttl_seconds):
        raise AssertionError("set_cache should not be called when cache hit")

    async def fake_invalidate(key):
        pass

    class Repo:
        async def create_grade(self, *args, **kwargs):
            return SimpleNamespace(
                id=uuid4(),
                student_id=student_id,
                lesson_id=uuid4(),
                value=5,
                comment=None,
                created_at=None,
            )

        async def list_for_student(self, sid):
            return []

    session = DummySession()
    service = GradeService(session=session)  # type: ignore
    service.repo = Repo()  # type: ignore
    monkeypatch.setattr("edutrack.application.grades.get_cache", fake_get_cache)
    monkeypatch.setattr("edutrack.application.grades.set_cache", fake_set_cache)
    monkeypatch.setattr("edutrack.application.grades.invalidate", fake_invalidate)

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

    called_invalidate = {"cnt": 0}

    async def fake_invalidate(key):
        called_invalidate["cnt"] += 1

    async def fake_get_cache(key):
        return None

    async def fake_set_cache(key, value, ttl_seconds):
        pass

    service = SchoolService(session=session)  # type: ignore
    service.repo = Repo()  # type: ignore
    monkeypatch.setattr("edutrack.application.schools.invalidate", fake_invalidate)
    monkeypatch.setattr("edutrack.application.schools.get_cache", fake_get_cache)
    monkeypatch.setattr("edutrack.application.schools.set_cache", fake_set_cache)

    school = await service.create_school("S1", None)
    assert called_invalidate["cnt"] == 1
    assert session.committed is True
    schools = await service.list_schools()
    assert len(schools) == 1

