from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SchoolCreate(BaseModel):
    name: str
    address: str | None = None


class SchoolResponse(BaseModel):
    id: UUID
    name: str
    address: str | None = None


class ClassCreate(BaseModel):
    school_id: UUID
    name: str
    grade_level: int


class ClassResponse(BaseModel):
    id: UUID
    school_id: UUID
    name: str
    grade_level: int


class StudentCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    school_id: UUID
    class_id: UUID | None = None


class StudentResponse(BaseModel):
    id: UUID
    user_id: UUID
    school_id: UUID


class LessonCreate(BaseModel):
    class_id: UUID
    subject_id: UUID
    teacher_id: UUID
    topic: str
    start_at: datetime
    end_at: datetime


class LessonResponse(BaseModel):
    id: UUID
    class_id: UUID
    subject_id: UUID
    teacher_id: UUID
    topic: str
    start_at: datetime
    end_at: datetime


class GradeCreate(BaseModel):
    student_id: UUID
    lesson_id: UUID
    value: int
    comment: str | None = None


class GradeResponse(BaseModel):
    id: UUID
    student_id: UUID
    lesson_id: UUID
    value: int
    comment: str | None = None
    created_at: datetime


class GradeList(BaseModel):
    items: list[GradeResponse]


class MessageCreate(BaseModel):
    subject: str
    body: str
    recipient_user_ids: list[UUID]


class MessageResponse(BaseModel):
    id: UUID
    sender_id: UUID
    subject: str
    body: str
    created_at: datetime


class EmailSendRequest(BaseModel):
    recipients: list[EmailStr]


class SubjectCreate(BaseModel):
    name: str


class SubjectResponse(BaseModel):
    id: UUID
    name: str


# Восстановление пароля
class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


# Профиль пользователя
class ProfileUpdate(BaseModel):
    full_name: str | None = None
    date_of_birth: date | None = None
    show_birthday: bool | None = None
    avatar_url: str | None = None


class ProfileResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    date_of_birth: date | None = None
    show_birthday: bool
    avatar_url: str | None = None
    created_at: datetime


# Встроенный мессенджер
class DirectMessageCreate(BaseModel):
    recipient_id: UUID
    content: str


class DirectMessageResponse(BaseModel):
    id: UUID
    sender_id: UUID
    recipient_id: UUID
    content: str
    read: bool
    created_at: datetime


class DirectMessageList(BaseModel):
    items: list[DirectMessageResponse]


# Одногруппники
class ClassmateResponse(BaseModel):
    user_id: UUID
    full_name: str
    avatar_url: str | None = None
    date_of_birth: date | None = None
    show_birthday: bool


class ClassmatesList(BaseModel):
    items: list[ClassmateResponse]


# Новости
class NewsCreate(BaseModel):
    school_id: UUID
    title: str
    content: str
    preview_image_url: str | None = None
    published_at: datetime | None = None  # None = черновик, будущее = запланировано


class NewsPreview(BaseModel):
    id: UUID
    title: str
    preview_image_url: str | None = None
    published_at: datetime | None = None


class NewsPreviewList(BaseModel):
    items: list[NewsPreview]


class NewsResponse(BaseModel):
    id: UUID
    school_id: UUID
    author_id: UUID
    author_name: str
    title: str
    content: str
    preview_image_url: str | None = None
    published_at: datetime | None = None
    created_at: datetime


# Промежуточная аттестация
class InterimAssessmentResponse(BaseModel):
    id: UUID
    student_id: UUID
    subject_id: UUID
    subject_name: str
    school_year: int
    semester: int
    grade: int
    comment: str | None = None
    created_at: datetime


class InterimAssessmentList(BaseModel):
    items: list[InterimAssessmentResponse]


# Успеваемость
class GradeStatistics(BaseModel):
    subject_id: UUID
    subject_name: str
    grade_count: int
    average_grade: float | None = None
    grades: list[int]


class PerformanceResponse(BaseModel):
    month: int
    year: int
    statistics: list[GradeStatistics]
