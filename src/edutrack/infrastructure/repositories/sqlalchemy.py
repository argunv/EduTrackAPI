from collections.abc import Iterable
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from edutrack.domain.repositories import (
    ClassRepository,
    DirectMessageRepository,
    EmailOutboxRepository,
    GradeRepository,
    InterimAssessmentRepository,
    LessonRepository,
    MessageRepository,
    NewsRepository,
    PasswordResetTokenRepository,
    SchoolRepository,
    StudentRepository,
    UserRepository,
)
from edutrack.infrastructure.db import models
from edutrack.infrastructure.db.models import UserRole, UserRoleAssignment


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> models.User | None:
        stmt = select(models.User).where(models.User.email == email)
        return await self.session.scalar(stmt)

    async def get_by_id(self, user_id: UUID) -> models.User | None:
        stmt = select(models.User).where(models.User.id == user_id)
        return await self.session.scalar(stmt)

    async def create_user(
        self, email: str, full_name: str, password_hash: str, roles: list[str] | None = None
    ) -> models.User:
        user = models.User(email=email, full_name=full_name, password_hash=password_hash)
        self.session.add(user)
        await self.session.flush()

        # Назначаем роли, если указаны
        if roles:
            for role_str in roles:
                try:
                    role = UserRole(role_str)
                    role_assignment = UserRoleAssignment(user_id=user.id, role=role)
                    self.session.add(role_assignment)
                except ValueError:
                    # Игнорируем невалидные роли
                    pass

        await self.session.flush()
        return user

    async def assign_role(self, user_id: UUID, role: str, assigned_by: UUID | None = None) -> UserRoleAssignment:
        role_enum = UserRole(role)
        role_assignment = UserRoleAssignment(user_id=user_id, role=role_enum, assigned_by=assigned_by)
        self.session.add(role_assignment)
        await self.session.flush()
        return role_assignment

    async def remove_role(self, user_id: UUID, role: str) -> None:
        role_enum = UserRole(role)
        stmt = select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.role == role_enum,
        )
        role_assignment = await self.session.scalar(stmt)
        if role_assignment:
            await self.session.delete(role_assignment)
            await self.session.flush()

    async def update_profile(self, user_id: UUID, full_name: str | None = None, date_of_birth: date | None = None, show_birthday: bool | None = None, avatar_url: str | None = None) -> models.User:
        # Обновляем основную информацию пользователя
        if full_name is not None:
            stmt = update(models.User).where(models.User.id == user_id).values(full_name=full_name)
            await self.session.execute(stmt)

        # Обновляем или создаем профиль пользователя
        profile_data = {}
        if date_of_birth is not None:
            profile_data["date_of_birth"] = date_of_birth
        if show_birthday is not None:
            profile_data["show_birthday"] = show_birthday
        if avatar_url is not None:
            profile_data["avatar_url"] = avatar_url

        if profile_data:
            # Проверяем, существует ли профиль
            stmt = select(models.UserProfile).where(models.UserProfile.user_id == user_id)
            existing_profile = await self.session.scalar(stmt)

            if existing_profile:
                # Обновляем существующий профиль
                for key, value in profile_data.items():
                    setattr(existing_profile, key, value)
                existing_profile.updated_at = datetime.now(UTC)
            else:
                # Создаем новый профиль
                profile = models.UserProfile(user_id=user_id, **profile_data)
                self.session.add(profile)

            await self.session.flush()

        return await self.get_by_id(user_id)


class SqlAlchemySchoolRepository(SchoolRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_school(self, name: str, address: str | None) -> models.School:
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

    async def list_classes(self, school_id: UUID | None = None):
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

    async def get(self, student_id: UUID) -> models.Student | None:
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

    async def create_grade(self, student_id: UUID, lesson_id: UUID, value: int, comment: str | None):
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

    async def get(self, message_id: UUID) -> models.Message | None:
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
            .values(status=models.MessageDeliveryStatus.sent, sent_at=datetime.now(UTC), last_error=None)
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

    async def get_pending(self, outbox_id: UUID) -> models.EmailOutbox | None:
        stmt = select(models.EmailOutbox).where(models.EmailOutbox.id == outbox_id)
        return await self.session.scalar(stmt)


class SqlAlchemyPasswordResetTokenRepository(PasswordResetTokenRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_token(self, user_id: UUID, token: str, expires_at: datetime) -> models.PasswordResetToken:
        # Удаляем старые токены для этого пользователя
        delete_stmt = delete(models.PasswordResetToken).where(models.PasswordResetToken.user_id == user_id)
        await self.session.execute(delete_stmt)

        reset_token = models.PasswordResetToken(user_id=user_id, token=token, expires_at=expires_at)
        self.session.add(reset_token)
        await self.session.flush()
        return reset_token

    async def get_by_token(self, token: str) -> models.PasswordResetToken | None:
        stmt = select(models.PasswordResetToken).where(
            models.PasswordResetToken.token == token,
            ~models.PasswordResetToken.used,
            models.PasswordResetToken.expires_at > datetime.now(UTC)
        )
        return await self.session.scalar(stmt)

    async def mark_as_used(self, token_id: UUID) -> None:
        stmt = update(models.PasswordResetToken).where(models.PasswordResetToken.id == token_id).values(used=True)
        await self.session.execute(stmt)
        await self.session.flush()


class SqlAlchemyDirectMessageRepository(DirectMessageRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_message(self, sender_id: UUID, recipient_id: UUID, content: str) -> models.DirectMessage:
        message = models.DirectMessage(sender_id=sender_id, recipient_id=recipient_id, content=content)
        self.session.add(message)
        await self.session.flush()
        return message

    async def get_conversation(self, user1_id: UUID, user2_id: UUID, limit: int = 50) -> Iterable[models.DirectMessage]:
        stmt = (
            select(models.DirectMessage)
            .where(
                or_(
                    and_(models.DirectMessage.sender_id == user1_id, models.DirectMessage.recipient_id == user2_id),
                    and_(models.DirectMessage.sender_id == user2_id, models.DirectMessage.recipient_id == user1_id),
                )
            )
            .order_by(models.DirectMessage.created_at.desc())
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return result.all()

    async def mark_as_read(self, message_id: UUID) -> None:
        stmt = update(models.DirectMessage).where(models.DirectMessage.id == message_id).values(read=True)
        await self.session.execute(stmt)
        await self.session.flush()

    async def get_unread_count(self, user_id: UUID) -> int:
        stmt = select(func.count(models.DirectMessage.id)).where(
            models.DirectMessage.recipient_id == user_id,
            ~models.DirectMessage.read
        )
        result = await self.session.scalar(stmt)
        return result or 0


class SqlAlchemyNewsRepository(NewsRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_news(self, school_id: UUID, author_id: UUID, title: str, content: str, preview_image_url: str | None = None, published_at: datetime | None = None) -> models.News:
        news = models.News(
            school_id=school_id,
            author_id=author_id,
            title=title,
            content=content,
            preview_image_url=preview_image_url,
            published_at=published_at
        )
        self.session.add(news)
        await self.session.flush()
        return news

    async def get_preview_list(self, school_id: UUID | None = None, limit: int = 20) -> Iterable[models.News]:
        now = datetime.now(UTC)
        stmt = (
            select(models.News)
            .where(
                models.News.published_at <= now,
                models.News.published_at.isnot(None)
            )
            .order_by(models.News.published_at.desc())
            .limit(limit)
        )
        if school_id:
            stmt = stmt.where(models.News.school_id == school_id)
        result = await self.session.scalars(stmt)
        return result.all()

    async def get_by_id(self, news_id: UUID) -> models.News | None:
        stmt = select(models.News).where(models.News.id == news_id)
        return await self.session.scalar(stmt)


class SqlAlchemyInterimAssessmentRepository(InterimAssessmentRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_assessment(self, student_id: UUID, subject_id: UUID, school_year: int, semester: int, grade: int, comment: str | None = None) -> models.InterimAssessment:
        assessment = models.InterimAssessment(
            student_id=student_id,
            subject_id=subject_id,
            school_year=school_year,
            semester=semester,
            grade=grade,
            comment=comment
        )
        self.session.add(assessment)
        await self.session.flush()
        return assessment

    async def get_by_student(self, student_id: UUID, school_year: int | None = None) -> Iterable[models.InterimAssessment]:
        stmt = select(models.InterimAssessment).where(models.InterimAssessment.student_id == student_id)
        if school_year:
            stmt = stmt.where(models.InterimAssessment.school_year == school_year)
        stmt = stmt.order_by(models.InterimAssessment.school_year.desc(), models.InterimAssessment.semester.desc())
        result = await self.session.scalars(stmt)
        return result.all()
