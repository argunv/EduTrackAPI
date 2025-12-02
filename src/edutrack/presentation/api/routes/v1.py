from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from edutrack.application.auth import AuthService
from edutrack.application.schools import SchoolService
from edutrack.application.classes import ClassService
from edutrack.application.students import StudentService
from edutrack.application.lessons import LessonService
from edutrack.application.grades import GradeService
from edutrack.application.messages import MessageService
from edutrack.presentation.api.schemas import (
    LoginRequest,
    TokenResponse,
    SchoolCreate,
    SchoolResponse,
    ClassCreate,
    ClassResponse,
    StudentCreate,
    StudentResponse,
    LessonCreate,
    LessonResponse,
    GradeCreate,
    GradeResponse,
    GradeList,
    MessageCreate,
    MessageResponse,
    EmailSendRequest,
)
from edutrack.presentation.api.dependencies.auth import get_current_user
from edutrack.infrastructure.db.database import get_session


router = APIRouter(prefix="/api/v1")


@router.post("/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)):
    service = AuthService(session)
    token = await service.authenticate(email=payload.email, password=payload.password)
    return TokenResponse(access_token=token)


@router.post("/schools", response_model=SchoolResponse, status_code=status.HTTP_201_CREATED)
async def create_school(
    payload: SchoolCreate,
    session: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
):
    service = SchoolService(session)
    school = await service.create_school(name=payload.name, address=payload.address)
    return SchoolResponse(id=school.id, name=school.name, address=school.address)


@router.post("/classes", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
async def create_class(
    payload: ClassCreate,
    session: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
):
    service = ClassService(session)
    class_ = await service.create_class(
        school_id=payload.school_id, name=payload.name, grade_level=payload.grade_level
    )
    return ClassResponse(id=class_.id, school_id=class_.school_id, name=class_.name, grade_level=class_.grade_level)


@router.post("/students", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student(
    payload: StudentCreate,
    session: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
):
    service = StudentService(session)
    student = await service.create_student(
        email=payload.email,
        full_name=payload.full_name,
        password=payload.password,
        school_id=payload.school_id,
        class_id=payload.class_id,
    )
    return StudentResponse(id=student.id, user_id=student.user_id, school_id=student.school_id)


@router.post("/lessons", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    payload: LessonCreate,
    session: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
):
    service = LessonService(session)
    lesson = await service.create_lesson(
        class_id=payload.class_id,
        subject_id=payload.subject_id,
        teacher_id=payload.teacher_id,
        topic=payload.topic,
        start_at=payload.start_at,
        end_at=payload.end_at,
    )
    return LessonResponse(
        id=lesson.id,
        class_id=lesson.class_id,
        subject_id=lesson.subject_id,
        teacher_id=lesson.teacher_id,
        topic=lesson.topic,
        start_at=lesson.start_at,
        end_at=lesson.end_at,
    )


@router.post("/grades", response_model=GradeResponse, status_code=status.HTTP_201_CREATED)
async def create_grade(
    payload: GradeCreate,
    session: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
):
    service = GradeService(session)
    grade = await service.create_grade(
        student_id=payload.student_id,
        lesson_id=payload.lesson_id,
        value=payload.value,
        comment=payload.comment,
    )
    return GradeResponse(
        id=grade.id,
        student_id=grade.student_id,
        lesson_id=grade.lesson_id,
        value=grade.value,
        comment=grade.comment,
        created_at=grade.created_at,
    )


@router.get("/students/{student_id}/grades", response_model=GradeList)
async def list_student_grades(student_id: UUID, session: AsyncSession = Depends(get_session), _user=Depends(get_current_user)):
    service = GradeService(session)
    grades = await service.list_grades(student_id=student_id)
    return GradeList(items=[GradeResponse(**g) if isinstance(g, dict) else GradeResponse(
        id=g.id,
        student_id=g.student_id,
        lesson_id=g.lesson_id,
        value=g.value,
        comment=g.comment,
        created_at=g.created_at,
    ) for g in grades])


@router.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    payload: MessageCreate,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    service = MessageService(session)
    message = await service.create_message(
        sender_id=current_user.id,
        subject=payload.subject,
        body=payload.body,
        recipient_user_ids=payload.recipient_user_ids,
    )
    return MessageResponse(
        id=message.id,
        sender_id=message.sender_id,
        subject=message.subject,
        body=message.body,
        created_at=message.created_at,
    )


@router.post("/messages/{message_id}/send-email", status_code=status.HTTP_202_ACCEPTED)
async def send_message_email(
    message_id: UUID,
    payload: EmailSendRequest,
    session: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
):
    service = MessageService(session)
    outbox = await service.enqueue_email(message_id=message_id, recipients_emails=payload.recipients)
    return {"outbox_id": str(outbox.id), "status": outbox.status.value}





