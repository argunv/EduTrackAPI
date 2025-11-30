from datetime import datetime, date
from typing import List
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
    items: List[GradeResponse]


class MessageCreate(BaseModel):
    subject: str
    body: str
    recipient_user_ids: List[UUID]


class MessageResponse(BaseModel):
    id: UUID
    sender_id: UUID
    subject: str
    body: str
    created_at: datetime


class EmailSendRequest(BaseModel):
    recipients: List[EmailStr]





