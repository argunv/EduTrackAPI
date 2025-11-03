from abc import ABC, abstractmethod
from typing import Any, Iterable, Optional
from uuid import UUID


class UserRepository(ABC):
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[Any]:
        raise NotImplementedError

    @abstractmethod
    async def create_user(self, email: str, full_name: str, password_hash: str, role: str) -> Any:
        raise NotImplementedError


class SchoolRepository(ABC):
    @abstractmethod
    async def create_school(self, name: str, address: Optional[str]) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def list_schools(self) -> Iterable[Any]:
        raise NotImplementedError


class ClassRepository(ABC):
    @abstractmethod
    async def create_class(self, school_id: UUID, name: str, grade_level: int) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def list_classes(self, school_id: Optional[UUID] = None) -> Iterable[Any]:
        raise NotImplementedError


class StudentRepository(ABC):
    @abstractmethod
    async def create_student(self, user_id: UUID, school_id: UUID) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def assign_to_class(self, student_id: UUID, class_id: UUID) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def get(self, student_id: UUID) -> Optional[Any]:
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
    async def create_grade(self, student_id: UUID, lesson_id: UUID, value: int, comment: Optional[str]) -> Any:
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
    async def get(self, message_id: UUID) -> Optional[Any]:
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
    async def get_pending(self, outbox_id: UUID) -> Optional[Any]:
        raise NotImplementedError





