import enum
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDMixin


class UserRole(str, enum.Enum):
    """Роли пользователей в системе электронного журнала."""
    # Базовые роли
    student = "student"
    guardian = "guardian"

    # Педагогический состав
    teacher = "teacher"  # Обычный учитель
    class_teacher = "class_teacher"  # Классный руководитель
    subject_teacher = "subject_teacher"  # Учитель-предметник

    # Административный состав
    head_teacher = "head_teacher"  # Завуч
    director = "director"  # Директор
    deputy_director = "deputy_director"  # Заместитель директора

    # Специалисты
    methodist = "methodist"  # Методист
    scheduler = "scheduler"  # Составитель расписания
    psychologist = "psychologist"  # Психолог
    librarian = "librarian"  # Библиотекарь

    # Технический персонал
    admin = "admin"  # Системный администратор
    secretary = "secretary"  # Секретарь


class AttendanceStatus(str, enum.Enum):
    present = "present"
    absent = "absent"
    late = "late"


class MessageDeliveryStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class UserRoleAssignment(Base):
    """Связующая таблица для множественных ролей пользователя."""
    __tablename__ = "user_role_assignments"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="userrole_new", create_type=False), primary_key=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    user = relationship("User", foreign_keys=[user_id], back_populates="role_assignments")


class UserProfile(Base):
    """Профиль пользователя (дополнительные данные, загружаются по требованию)."""
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True, unique=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    show_birthday: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    user = relationship("User", back_populates="user_profile")


class User(Base, UUIDMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    role_assignments = relationship(
        "UserRoleAssignment",
        primaryjoin="User.id == UserRoleAssignment.user_id",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    student_profile = relationship("Student", back_populates="user", uselist=False)
    teacher_profile = relationship("Teacher", back_populates="user", uselist=False)
    guardian_profile = relationship("Guardian", back_populates="user", uselist=False)
    user_profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sent_direct_messages = relationship("DirectMessage", foreign_keys="DirectMessage.sender_id", back_populates="sender")
    received_direct_messages = relationship("DirectMessage", foreign_keys="DirectMessage.recipient_id", back_populates="recipient")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")


class School(Base, UUIDMixin):
    __tablename__ = "schools"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    classes = relationship("Class", back_populates="school")
    students = relationship("Student", back_populates="school")
    news = relationship("News", back_populates="school")


class Class(Base, UUIDMixin):
    __tablename__ = "classes"

    school_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("schools.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    grade_level: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    school = relationship("School", back_populates="classes")
    students = relationship("ClassStudent", back_populates="class_")
    subjects = relationship("ClassSubject", back_populates="class_")
    lessons = relationship("Lesson", back_populates="class_")

    __table_args__ = (UniqueConstraint("school_id", "name", name="uq_class_school_name"),)


class Student(Base, UUIDMixin):
    __tablename__ = "students"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    school_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("schools.id"), nullable=False)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    user = relationship("User", back_populates="student_profile")
    school = relationship("School", back_populates="students")
    classes = relationship("ClassStudent", back_populates="student")
    grades = relationship("Grade", back_populates="student")
    attendance = relationship("Attendance", back_populates="student")
    submissions = relationship("HomeworkSubmission", back_populates="student")
    interim_assessments = relationship("InterimAssessment", back_populates="student")


class Teacher(Base, UUIDMixin):
    __tablename__ = "teachers"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    school_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("schools.id"), nullable=False)
    hired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    user = relationship("User", back_populates="teacher_profile")
    school = relationship("School")
    subjects = relationship("ClassSubject", back_populates="teacher")
    lessons = relationship("Lesson", back_populates="teacher")


class Guardian(Base, UUIDMixin):
    __tablename__ = "guardians"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    user = relationship("User", back_populates="guardian_profile")
    students = relationship("StudentGuardian", back_populates="guardian")


class StudentGuardian(Base):
    __tablename__ = "student_guardians"
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("students.id"), primary_key=True)
    guardian_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("guardians.id"), primary_key=True)

    student = relationship("Student")
    guardian = relationship("Guardian", back_populates="students")


class ClassStudent(Base):
    __tablename__ = "class_students"
    class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("classes.id"), primary_key=True)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("students.id"), primary_key=True)

    class_ = relationship("Class", back_populates="students")
    student = relationship("Student", back_populates="classes")


class Subject(Base, UUIDMixin):
    __tablename__ = "subjects"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    class_subjects = relationship("ClassSubject", back_populates="subject")
    lessons = relationship("Lesson", back_populates="subject")


class ClassSubject(Base):
    __tablename__ = "class_subjects"
    class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("classes.id"), primary_key=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subjects.id"), primary_key=True)
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("teachers.id"))

    class_ = relationship("Class", back_populates="subjects")
    subject = relationship("Subject", back_populates="class_subjects")
    teacher = relationship("Teacher", back_populates="subjects")


class Lesson(Base, UUIDMixin):
    __tablename__ = "lessons"

    class_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("classes.id"), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=False)
    teacher_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teachers.id"), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    class_ = relationship("Class", back_populates="lessons")
    subject = relationship("Subject", back_populates="lessons")
    teacher = relationship("Teacher", back_populates="lessons")
    grades = relationship("Grade", back_populates="lesson")
    attendance = relationship("Attendance", back_populates="lesson")
    homework = relationship("Homework", back_populates="lesson", uselist=False)


class Grade(Base, UUIDMixin):
    __tablename__ = "grades"

    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False)
    lesson_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("lessons.id"), nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    student = relationship("Student", back_populates="grades")
    lesson = relationship("Lesson", back_populates="grades")


class Attendance(Base, UUIDMixin):
    __tablename__ = "attendance"

    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False)
    lesson_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("lessons.id"), nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(Enum(AttendanceStatus), nullable=False)
    noted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    student = relationship("Student", back_populates="attendance")
    lesson = relationship("Lesson", back_populates="attendance")


class Homework(Base, UUIDMixin):
    __tablename__ = "homeworks"

    lesson_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("lessons.id"), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)

    lesson = relationship("Lesson", back_populates="homework")
    submissions = relationship("HomeworkSubmission", back_populates="homework")


class HomeworkSubmission(Base, UUIDMixin):
    __tablename__ = "homework_submissions"

    homework_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("homeworks.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    grade: Mapped[int | None] = mapped_column(Integer)

    homework = relationship("Homework", back_populates="submissions")
    student = relationship("Student", back_populates="submissions")

    __table_args__ = (UniqueConstraint("homework_id", "student_id", name="uq_homework_submission"),)


class Message(Base, UUIDMixin):
    __tablename__ = "messages"

    sender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    sender = relationship("User")
    recipients = relationship("MessageRecipient", back_populates="message")
    outbox_entries = relationship("EmailOutbox", back_populates="message")


class MessageRecipient(Base):
    __tablename__ = "message_recipients"

    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("messages.id"), primary_key=True)
    recipient_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    message = relationship("Message", back_populates="recipients")
    recipient_user = relationship("User")


class EmailOutbox(Base, UUIDMixin):
    __tablename__ = "email_outbox"

    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False)
    recipients: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[MessageDeliveryStatus] = mapped_column(
        Enum(MessageDeliveryStatus), default=MessageDeliveryStatus.pending, nullable=False
    )
    retries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    message = relationship("Message", back_populates="outbox_entries")


class PasswordResetToken(Base, UUIDMixin):
    """Токен для восстановления пароля."""
    __tablename__ = "password_reset_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    user = relationship("User", back_populates="password_reset_tokens")


class DirectMessage(Base, UUIDMixin):
    """Встроенный мессенджер - сообщения между пользователями."""
    __tablename__ = "direct_messages"

    sender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    recipient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_direct_messages")
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="received_direct_messages")


class News(Base, UUIDMixin):
    """Новости школы."""
    __tablename__ = "news"

    school_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("schools.id"), nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    preview_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # None = черновик, будущее время = запланировано
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    school = relationship("School", back_populates="news")
    author = relationship("User")


class InterimAssessment(Base, UUIDMixin):
    """Промежуточная аттестация (обычно 1 раз в год)."""
    __tablename__ = "interim_assessments"

    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=False)
    school_year: Mapped[int] = mapped_column(Integer, nullable=False)  # Учебный год (например, 2024)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)  # Семестр (1 или 2)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)  # Оценка за аттестацию
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    student = relationship("Student", back_populates="interim_assessments")
    subject = relationship("Subject")

    __table_args__ = (UniqueConstraint("student_id", "subject_id", "school_year", "semester", name="uq_interim_assessment"),)
