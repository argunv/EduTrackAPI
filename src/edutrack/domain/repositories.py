from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any
from uuid import UUID


class UserRepository(ABC):
    @abstractmethod
    async def get_by_email(self, email: str) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    async def create_user(self, email: str, full_name: str, password_hash: str, roles: list[str] | None = None) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def assign_role(self, user_id: UUID, role: str, assigned_by: UUID | None = None) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def remove_role(self, user_id: UUID, role: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def update_profile(self, user_id: UUID, full_name: str | None = None, date_of_birth: Any | None = None, show_birthday: bool | None = None, avatar_url: str | None = None) -> Any:
        raise NotImplementedError


class SchoolRepository(ABC):
    @abstractmethod
    async def create_school(self, name: str, address: str | None) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def list_schools(self) -> Iterable[Any]:
        raise NotImplementedError


class ClassRepository(ABC):
    @abstractmethod
    async def create_class(self, school_id: UUID, name: str, grade_level: int) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def list_classes(self, school_id: UUID | None = None) -> Iterable[Any]:
        raise NotImplementedError


class StudentRepository(ABC):
    @abstractmethod
    async def create_student(self, user_id: UUID, school_id: UUID) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def assign_to_class(self, student_id: UUID, class_id: UUID) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def get(self, student_id: UUID) -> Any | None:
        raise NotImplementedError


class LessonRepository(ABC):
    @abstractmethod
    async def create_lesson(self, class_id: UUID, subject_id: UUID, teacher_id: UUID, topic: str, start_at, end_at) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def list_for_class(self, class_id: UUID):
        raise NotImplementedError


class GradeRepository(ABC):
    @abstractmethod
    async def create_grade(self, student_id: UUID, lesson_id: UUID, value: int, comment: str | None) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def list_for_student(self, student_id: UUID):
        raise NotImplementedError


class MessageRepository(ABC):
    @abstractmethod
    async def create_message(self, sender_id: UUID, subject: str, body: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def add_recipients(self, message_id: UUID, recipients: list[UUID]) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def get(self, message_id: UUID) -> Any | None:
        raise NotImplementedError


class EmailOutboxRepository(ABC):
    @abstractmethod
    async def enqueue(self, message_id: UUID, recipients: list[str], subject: str, body: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def mark_sent(self, outbox_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    async def mark_failed(self, outbox_id: UUID, error: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_pending(self, outbox_id: UUID) -> Any | None:
        raise NotImplementedError


class PasswordResetTokenRepository(ABC):
    @abstractmethod
    async def create_token(self, user_id: UUID, token: str, expires_at: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def get_by_token(self, token: str) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    async def mark_as_used(self, token_id: UUID) -> None:
        raise NotImplementedError


class DirectMessageRepository(ABC):
    @abstractmethod
    async def create_message(self, sender_id: UUID, recipient_id: UUID, content: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def get_conversation(self, user1_id: UUID, user2_id: UUID, limit: int = 50) -> Iterable[Any]:
        raise NotImplementedError

    @abstractmethod
    async def mark_as_read(self, message_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_unread_count(self, user_id: UUID) -> int:
        raise NotImplementedError


class NewsRepository(ABC):
    @abstractmethod
    async def create_news(self, school_id: UUID, author_id: UUID, title: str, content: str, preview_image_url: str | None = None, published_at: Any | None = None) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def get_preview_list(self, school_id: UUID | None = None, limit: int = 20) -> Iterable[Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, news_id: UUID) -> Any | None:
        raise NotImplementedError


class InterimAssessmentRepository(ABC):
    @abstractmethod
    async def create_assessment(self, student_id: UUID, subject_id: UUID, school_year: int, semester: int, grade: int, comment: str | None = None) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def get_by_student(self, student_id: UUID, school_year: int | None = None) -> Iterable[Any]:
        raise NotImplementedError
