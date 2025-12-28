"""Фабрики для создания тестовых данных."""
from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import uuid4


class UserFactory:
    """Фабрика для создания тестовых пользователей."""

    @staticmethod
    def create_user(user_id=None, email="test@example.com", full_name="Test User", password_hash="hashed_password", **kwargs):
        """Создает тестового пользователя."""
        return SimpleNamespace(
            id=user_id or uuid4(),
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            **kwargs
        )

    @staticmethod
    def create_user_with_profile(user_id=None, **kwargs):
        """Создает пользователя с профилем."""
        user = UserFactory.create_user(user_id=user_id, **kwargs)
        user.user_profile = SimpleNamespace(
            date_of_birth=date(2000, 1, 1),
            show_birthday=False,
            avatar_url="https://example.com/avatar.jpg"
        )
        return user


class MessageFactory:
    """Фабрика для создания тестовых сообщений."""

    @staticmethod
    def create_message(message_id=None, sender_id=None, recipient_id=None, content="Test", **kwargs):
        """Создает тестовое сообщение."""
        return SimpleNamespace(
            id=message_id or uuid4(),
            sender_id=sender_id or uuid4(),
            recipient_id=recipient_id or uuid4(),
            content=content,
            read=False,
            **kwargs
        )


class NewsFactory:
    """Фабрика для создания тестовых новостей."""

    @staticmethod
    def create_news(news_id=None, school_id=None, author_id=None, **kwargs):
        """Создает тестовую новость."""
        return SimpleNamespace(
            id=news_id or uuid4(),
            school_id=school_id or uuid4(),
            author_id=author_id or uuid4(),
            title=kwargs.get("title", "Test News"),
            content=kwargs.get("content", "Test Content"),
            preview_image_url=kwargs.get("preview_image_url", "https://example.com/image.jpg"),
            published_at=kwargs.get("published_at", datetime.now(UTC)),
        )


class AssessmentFactory:
    """Фабрика для создания тестовых оценок."""

    @staticmethod
    def create_assessment(assessment_id=None, student_id=None, subject_id=None, **kwargs):
        """Создает тестовую оценку за промежуточную аттестацию."""
        return SimpleNamespace(
            id=assessment_id or uuid4(),
            student_id=student_id or uuid4(),
            subject_id=subject_id or uuid4(),
            school_year=kwargs.get("school_year", 2024),
            semester=kwargs.get("semester", 1),
            grade=kwargs.get("grade", 5),
            comment=kwargs.get("comment", "Отлично"),
        )


class GradeFactory:
    """Фабрика для создания тестовых оценок."""

    @staticmethod
    def create_grade(grade_id=None, student_id=None, lesson_id=None, **kwargs):
        """Создает тестовую оценку."""
        return SimpleNamespace(
            id=grade_id or uuid4(),
            student_id=student_id or uuid4(),
            lesson_id=lesson_id or uuid4(),
            value=kwargs.get("value", 5),
            comment=kwargs.get("comment", None),
            created_at=kwargs.get("created_at", datetime.now(UTC)),
        )


class LessonFactory:
    """Фабрика для создания тестовых уроков."""

    @staticmethod
    def create_lesson(lesson_id=None, class_id=None, subject_id=None, teacher_id=None, **kwargs):
        """Создает тестовый урок."""
        return SimpleNamespace(
            id=lesson_id or uuid4(),
            class_id=class_id or uuid4(),
            subject_id=subject_id or uuid4(),
            teacher_id=teacher_id or uuid4(),
            topic=kwargs.get("topic", "Test Topic"),
            start_at=kwargs.get("start_at", datetime.now(UTC)),
            end_at=kwargs.get("end_at", datetime.now(UTC)),
        )
