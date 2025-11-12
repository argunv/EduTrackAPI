from datetime import datetime
from typing import Iterable, Optional
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from edutrack.domain.repositories import (
    UserRepository,
    SchoolRepository,
    ClassRepository,
    StudentRepository,
    LessonRepository,
    GradeRepository,
    MessageRepository,
    EmailOutboxRepository,
)
from edutrack.infrastructure.db import models


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> Optional[models.User]:
        stmt = select(models.User).where(models.User.email == email)
        return await self.session.scalar(stmt)

    async def get_by_id(self, user_id: UUID) -> Optional[models.User]:
        stmt = select(models.User).where(models.User.id == user_id)
        return await self.session.scalar(stmt)

    async def create_user(self, email: str, full_name: str, password_hash: str, role: str) -> models.User:
        user = models.User(email=email, full_name=full_name, password_hash=password_hash, role=role)
        self.session.add(user)
        await self.session.flush()
        return user


class SqlAlchemySchoolRepository(SchoolRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_school(self, name: str, address: Optional[str]) -> models.School:
        school = models.School(name=name, address=address)
        self.session.add(school)
        await self.session.flush()
        return school

    async def list_schools(self) -> Iterable[models.School]:
        stmt = select(models.School).order_by(models.School.name)
        result = await self.session.scalars(stmt)
        return result.all()


class SqlAlchemyClassRepository(ClassRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_class(self, school_id: UUID, name: str, grade_level: int) -> models.Class:
        class_ = models.Class(school_id=school_id, name=name, grade_level=grade_level)
        self.session.add(class_)
        await self.session.flush()
        return class_

    async def list_classes(self, school_id: Optional[UUID] = None):
        stmt = select(models.Class)
        if school_id:
            stmt = stmt.where(models.Class.school_id == school_id)
        stmt = stmt.order_by(models.Class.grade_level, models.Class.name)
        result = await self.session.scalars(stmt)
        return result.all()


class SqlAlchemyStudentRepository(StudentRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_student(self, user_id: UUID, school_id: UUID) -> models.Student:
        student = models.Student(user_id=user_id, school_id=school_id)
        self.session.add(student)
        await self.session.flush()
        return student

    async def assign_to_class(self, student_id: UUID, class_id: UUID) -> models.ClassStudent:
        link = models.ClassStudent(student_id=student_id, class_id=class_id)
        self.session.add(link)
        await self.session.flush()
        return link

    async def get(self, student_id: UUID) -> Optional[models.Student]:
        stmt = select(models.Student).where(models.Student.id == student_id)
        return await self.session.scalar(stmt)


class SqlAlchemyLessonRepository(LessonRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_lesson(self, class_id: UUID, subject_id: UUID, teacher_id: UUID, topic: str, start_at, end_at):
        lesson = models.Lesson(
            class_id=class_id,
            subject_id=subject_id,
            teacher_id=teacher_id,
            topic=topic,
            start_at=start_at,
            end_at=end_at,
        )
        self.session.add(lesson)
        await self.session.flush()
        return lesson

    async def list_for_class(self, class_id: UUID):
        stmt = select(models.Lesson).where(models.Lesson.class_id == class_id).order_by(models.Lesson.start_at)
        result = await self.session.scalars(stmt)
        return result.all()


class SqlAlchemyGradeRepository(GradeRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_grade(self, student_id: UUID, lesson_id: UUID, value: int, comment: Optional[str]):
        grade = models.Grade(student_id=student_id, lesson_id=lesson_id, value=value, comment=comment)
        self.session.add(grade)
        await self.session.flush()
        return grade

    async def list_for_student(self, student_id: UUID):
        stmt = (
            select(models.Grade)
            .where(models.Grade.student_id == student_id)
            .order_by(models.Grade.created_at.desc())
        )
        result = await self.session.scalars(stmt)
        return result.all()


class SqlAlchemyMessageRepository(MessageRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_message(self, sender_id: UUID, subject: str, body: str) -> models.Message:
        message = models.Message(sender_id=sender_id, subject=subject, body=body)
        self.session.add(message)
        await self.session.flush()
        return message

    async def add_recipients(self, message_id: UUID, recipients: list[UUID]):
        for recipient_id in recipients:
            self.session.add(models.MessageRecipient(message_id=message_id, recipient_user_id=recipient_id))
        await self.session.flush()

    async def get(self, message_id: UUID) -> Optional[models.Message]:
        stmt = select(models.Message).where(models.Message.id == message_id)
        return await self.session.scalar(stmt)


class SqlAlchemyEmailOutboxRepository(EmailOutboxRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def enqueue(self, message_id: UUID, recipients: list[str], subject: str, body: str) -> models.EmailOutbox:
        outbox = models.EmailOutbox(
            message_id=message_id,
            recipients=recipients,
            subject=subject,
            body=body,
        )
        self.session.add(outbox)
        await self.session.flush()
        return outbox

    async def mark_sent(self, outbox_id: UUID) -> None:
        stmt = (
            update(models.EmailOutbox)
            .where(models.EmailOutbox.id == outbox_id)
            .values(status=models.MessageDeliveryStatus.sent, sent_at=datetime.utcnow(), last_error=None)
        )
        await self.session.execute(stmt)

    async def mark_failed(self, outbox_id: UUID, error: str) -> None:
        stmt = (
            update(models.EmailOutbox)
            .where(models.EmailOutbox.id == outbox_id)
            .values(
                status=models.MessageDeliveryStatus.failed,
                retries=models.EmailOutbox.retries + 1,
                last_error=error,
            )
        )
        await self.session.execute(stmt)

    async def get_pending(self, outbox_id: UUID) -> Optional[models.EmailOutbox]:
        stmt = select(models.EmailOutbox).where(models.EmailOutbox.id == outbox_id)
        return await self.session.scalar(stmt)





