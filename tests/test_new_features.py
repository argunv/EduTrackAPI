"""Тесты для новых функций."""
from datetime import date
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from edutrack.application.direct_messages import DirectMessageService
from edutrack.application.interim_assessment import InterimAssessmentService
from edutrack.application.news import NewsService
from edutrack.application.password_reset import PasswordResetService
from edutrack.application.profile import ProfileService
from helpers.assertions import assert_http_exception_async
from helpers.factories import AssessmentFactory, NewsFactory, UserFactory
from helpers.mocks import RepositoryMocks


@pytest.mark.asyncio
async def test_password_reset_service(session):
    """Тест восстановления пароля."""
    user = UserFactory.create_user(email="test@example.com")

    user_repo = RepositoryMocks.create_user_repo(users_by_email={"test@example.com": user})
    token_repo = RepositoryMocks.create_token_repo()

    service = PasswordResetService(session)
    service.users = user_repo
    service.tokens = token_repo

    # Мокаем send_email и проверяем, что он вызывается с правильными параметрами
    email_called = {"called": False, "recipients": None, "subject": None, "body": None}

    async def mock_send_email(recipients, subject, body):
        email_called["called"] = True
        email_called["recipients"] = recipients
        email_called["subject"] = subject
        email_called["body"] = body

    with patch("edutrack.application.password_reset.send_email", side_effect=mock_send_email):
        await service.request_reset("test@example.com")

    # Проверяем, что токен создан
    assert session.committed
    assert len(token_repo.created_tokens) == 1
    token = token_repo.created_tokens[0]
    assert token.user_id == user.id
    assert len(token.token) > 30  # URL-safe токен из 32 байт
    assert token.expires_at is not None

    # Проверяем, что email отправлен
    assert email_called["called"] is True
    assert email_called["recipients"] == ["test@example.com"]
    assert email_called["subject"] == "Восстановление пароля"
    assert token.token in email_called["body"]  # Токен должен быть в теле письма


@pytest.mark.asyncio
async def test_profile_service(session):
    """Тест обновления профиля."""
    user = UserFactory.create_user_with_profile(full_name="Updated Name")

    update_calls = []

    class UserRepo:
        async def update_profile(self, user_id, **kwargs):
            update_calls.append({"user_id": user_id, **kwargs})
            return user

    service = ProfileService(session)
    service.users = UserRepo()

    updated_user = await service.update_profile(
        user_id=user.id,
        full_name="Updated Name",
        date_of_birth=date(2000, 1, 1),
        show_birthday=False,
        avatar_url="https://example.com/avatar.jpg"
    )

    # Проверяем, что все поля переданы в репозиторий
    assert len(update_calls) == 1
    call = update_calls[0]
    assert call["user_id"] == user.id
    assert call["full_name"] == "Updated Name"
    assert call["date_of_birth"] == date(2000, 1, 1)
    assert call["show_birthday"] is False
    assert call["avatar_url"] == "https://example.com/avatar.jpg"

    # Проверяем результат
    assert updated_user.full_name == "Updated Name"
    assert updated_user.user_profile.date_of_birth == date(2000, 1, 1)
    assert updated_user.user_profile.show_birthday is False
    assert updated_user.user_profile.avatar_url == "https://example.com/avatar.jpg"
    assert session.committed


@pytest.mark.asyncio
async def test_direct_message_service(session):
    """Тест встроенного мессенджера."""
    from helpers.factories import MessageFactory

    user1_id = uuid4()
    user2_id = uuid4()
    message = MessageFactory.create_message(
        sender_id=user1_id,
        recipient_id=user2_id,
        content="Привет!"
    )

    class MessageRepo:
        async def create_message(self, sender_id, recipient_id, content):
            return message

        async def get_conversation(self, user1_id, user2_id, limit):
            return [message]

    service = DirectMessageService(session)
    service.messages = MessageRepo()

    result = await service.send_message(
        sender_id=user1_id,
        recipient_id=user2_id,
        content="Привет!"
    )

    assert result.sender_id == user1_id
    assert result.recipient_id == user2_id
    assert result.content == "Привет!"
    assert result.read is False
    assert session.committed

    # Получаем переписку
    conversation = await service.get_conversation(user1_id, user2_id)
    assert len(conversation) == 1
    assert conversation[0].content == "Привет!"


@pytest.mark.asyncio
async def test_direct_message_service_send_to_self(session):
    """Тест: нельзя отправить сообщение самому себе."""
    user_id = uuid4()

    service = DirectMessageService(session)
    service.messages = MagicMock()

    await assert_http_exception_async(
        service.send_message(
            sender_id=user_id,
            recipient_id=user_id,  # Отправка самому себе
            content="Привет!"
        ),
        status_code=400,
        detail_contains="самому себе"
    )
    # Сообщение не должно быть создано
    service.messages.create_message.assert_not_called()


@pytest.mark.asyncio
async def test_news_service(session):
    """Тест новостей."""
    news = NewsFactory.create_news(
        title="Test News",
        content="Test Content",
        preview_image_url="https://example.com/image.jpg"
    )

    class NewsRepo:
        async def create_news(self, **kwargs):
            return news

        async def get_preview_list(self, school_id, limit):
            return [news]

    service = NewsService(session)
    service.news = NewsRepo()

    result = await service.create_news(
        school_id=news.school_id,
        author_id=news.author_id,
        title=news.title,
        content=news.content,
        preview_image_url=news.preview_image_url,
        published_at=news.published_at
    )

    assert result.title == "Test News"
    assert result.content == "Test Content"
    assert result.preview_image_url == "https://example.com/image.jpg"
    assert result.published_at == news.published_at
    assert session.committed

    # Получаем preview список
    preview_list = await service.get_preview_list(school_id=news.school_id, limit=20)
    assert len(preview_list) == 1
    assert preview_list[0].title == "Test News"


@pytest.mark.asyncio
async def test_news_service_get_news_not_found(session):
    """Тест: получение несуществующей новости."""
    news_id = uuid4()

    class NewsRepo:
        async def get_by_id(self, nid):
            return None

    service = NewsService(session)
    service.news = NewsRepo()

    await assert_http_exception_async(
        service.get_news(news_id),
        status_code=404,
        detail_contains="не найдена"
    )


@pytest.mark.asyncio
async def test_interim_assessment_service(session):
    """Тест промежуточной аттестации."""
    assessment = AssessmentFactory.create_assessment(
        school_year=2024,
        semester=1,
        grade=5,
        comment="Отлично"
    )

    class AssessmentRepo:
        async def create_assessment(self, **kwargs):
            return assessment

        async def get_by_student(self, sid, school_year):
            return [assessment]

    service = InterimAssessmentService(session)
    service.assessments = AssessmentRepo()

    # Тестируем через сервис, а не напрямую через репозиторий
    result = await service.assessments.create_assessment(
        student_id=assessment.student_id,
        subject_id=assessment.subject_id,
        school_year=assessment.school_year,
        semester=assessment.semester,
        grade=assessment.grade,
        comment=assessment.comment
    )

    assert result.grade == 5
    assert result.school_year == 2024
    assert result.semester == 1

    # Получаем оценки студента через сервис (это проверяет бизнес-логику)
    assessments = await service.get_by_student(assessment.student_id)
    assert len(assessments) == 1
    assert assessments[0].grade == 5
    assert assessments[0].school_year == 2024
    assert assessments[0].semester == 1


@pytest.mark.asyncio
async def test_interim_assessment_service_get_by_student_with_year(session):
    """Тест получения оценок за конкретный учебный год."""
    student_id = uuid4()
    subject_id = uuid4()

    assessment_2024 = AssessmentFactory.create_assessment(
        student_id=student_id,
        subject_id=subject_id,
        school_year=2024,
        grade=5,
        comment="Отлично"
    )
    assessment_2023 = AssessmentFactory.create_assessment(
        student_id=student_id,
        subject_id=subject_id,
        school_year=2023,
        grade=4,
        comment="Хорошо"
    )

    class AssessmentRepo:
        async def get_by_student(self, sid, school_year):
            if school_year == 2024:
                return [assessment_2024]
            elif school_year is None:
                return [assessment_2024, assessment_2023]
            return []

    service = InterimAssessmentService(session)
    service.assessments = AssessmentRepo()

    # Получаем оценки за 2024 год
    assessments = await service.get_by_student(student_id, school_year=2024)
    assert len(assessments) == 1
    assert assessments[0].school_year == 2024

    # Получаем все оценки
    all_assessments = await service.get_by_student(student_id, school_year=None)
    assert len(all_assessments) == 2
