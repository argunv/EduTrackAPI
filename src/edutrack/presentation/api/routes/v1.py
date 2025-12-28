from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from edutrack.application.auth import AuthService
from edutrack.application.classes import ClassService
from edutrack.application.classmates import ClassmatesService
from edutrack.application.direct_messages import DirectMessageService
from edutrack.application.grades import GradeService
from edutrack.application.interim_assessment import InterimAssessmentService
from edutrack.application.lessons import LessonService
from edutrack.application.messages import MessageService
from edutrack.application.news import NewsService
from edutrack.application.password_reset import PasswordResetService
from edutrack.application.performance import PerformanceService
from edutrack.application.profile import ProfileService
from edutrack.application.schools import SchoolService
from edutrack.application.students import StudentService
from edutrack.application.subjects import SubjectService
from edutrack.infrastructure.db.database import get_session
from edutrack.presentation.api.dependencies.auth import (
    get_current_user,
    require_admin,
    require_staff,
)
from edutrack.presentation.api.schemas import (
    ClassCreate,
    ClassmateResponse,
    ClassmatesList,
    ClassResponse,
    DirectMessageCreate,
    DirectMessageList,
    DirectMessageResponse,
    EmailSendRequest,
    GradeCreate,
    GradeList,
    GradeResponse,
    GradeStatistics,
    InterimAssessmentList,
    InterimAssessmentResponse,
    LessonCreate,
    LessonResponse,
    LoginRequest,
    MessageCreate,
    MessageResponse,
    NewsCreate,
    NewsPreview,
    NewsPreviewList,
    NewsResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    PerformanceResponse,
    ProfileResponse,
    ProfileUpdate,
    SchoolCreate,
    SchoolResponse,
    StudentCreate,
    StudentResponse,
    SubjectCreate,
    SubjectResponse,
    TokenResponse,
)

router = APIRouter(prefix="/api/v1", tags=["v1"])


@router.post("/auth/login", response_model=TokenResponse, tags=["auth"])
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)):
    service = AuthService(session)
    token = await service.authenticate(email=payload.email, password=payload.password)
    return TokenResponse(access_token=token)


@router.post("/schools", response_model=SchoolResponse, status_code=status.HTTP_201_CREATED, tags=["admin"])
async def create_school(
    payload: SchoolCreate,
    session: AsyncSession = Depends(get_session),
    _user=Depends(require_admin),
):
    service = SchoolService(session)
    school = await service.create_school(name=payload.name, address=payload.address)
    return SchoolResponse(id=school.id, name=school.name, address=school.address)


@router.post("/classes", response_model=ClassResponse, status_code=status.HTTP_201_CREATED, tags=["admin"])
async def create_class(
    payload: ClassCreate,
    session: AsyncSession = Depends(get_session),
    _user=Depends(require_admin),
):
    service = ClassService(session)
    class_ = await service.create_class(
        school_id=payload.school_id, name=payload.name, grade_level=payload.grade_level
    )
    return ClassResponse(id=class_.id, school_id=class_.school_id, name=class_.name, grade_level=class_.grade_level)


@router.post("/students", response_model=StudentResponse, status_code=status.HTTP_201_CREATED, tags=["admin"])
async def create_student(
    payload: StudentCreate,
    session: AsyncSession = Depends(get_session),
    _user=Depends(require_admin),
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


@router.post("/subjects", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED, tags=["admin"])
async def create_subject(
    payload: SubjectCreate,
    session: AsyncSession = Depends(get_session),
    _user=Depends(require_admin),
):
    service = SubjectService(session)
    subject = await service.create_subject(name=payload.name)
    return SubjectResponse(id=subject.id, name=subject.name)


@router.get("/subjects", response_model=list[SubjectResponse], tags=["staff"])
async def list_subjects(
    session: AsyncSession = Depends(get_session),
    _user=Depends(require_staff),
):
    service = SubjectService(session)
    subjects = await service.list_subjects()
    return [SubjectResponse(id=UUID(s["id"]), name=s["name"]) for s in subjects]


@router.post("/lessons", response_model=LessonResponse, status_code=status.HTTP_201_CREATED, tags=["staff"])
async def create_lesson(
    payload: LessonCreate,
    session: AsyncSession = Depends(get_session),
    _user=Depends(require_staff),
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


@router.post("/grades", response_model=GradeResponse, status_code=status.HTTP_201_CREATED, tags=["staff"])
async def create_grade(
    payload: GradeCreate,
    session: AsyncSession = Depends(get_session),
    _user=Depends(require_staff),
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


@router.get("/students/{student_id}/grades", response_model=GradeList, tags=["staff"])
async def list_student_grades(student_id: UUID, session: AsyncSession = Depends(get_session), _user=Depends(require_staff)):
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


@router.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED, tags=["user"])
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


@router.post("/messages/{message_id}/send-email", status_code=status.HTTP_202_ACCEPTED, tags=["staff"])
async def send_message_email(
    message_id: UUID,
    payload: EmailSendRequest,
    session: AsyncSession = Depends(get_session),
    _user=Depends(require_staff),
):
    service = MessageService(session)
    outbox = await service.enqueue_email(message_id=message_id, recipients_emails=payload.recipients)
    return {"outbox_id": str(outbox.id), "status": outbox.status.value}


# Восстановление пароля
@router.post("/auth/password-reset/request", status_code=status.HTTP_202_ACCEPTED, tags=["auth"])
async def request_password_reset(
    payload: PasswordResetRequest,
    session: AsyncSession = Depends(get_session),
):
    service = PasswordResetService(session)
    await service.request_reset(email=payload.email)
    return {"message": "Если пользователь с таким email существует, письмо отправлено"}


@router.post("/auth/password-reset/confirm", status_code=status.HTTP_200_OK, tags=["auth"])
async def confirm_password_reset(
    payload: PasswordResetConfirm,
    session: AsyncSession = Depends(get_session),
):
    service = PasswordResetService(session)
    await service.reset_password(token=payload.token, new_password=payload.new_password)
    return {"message": "Пароль успешно изменен"}


# Профиль пользователя
@router.get("/profile", response_model=ProfileResponse, tags=["user"])
async def get_profile(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = ProfileService(session)
    user = await service.get_profile(current_user.id)
    profile = user.user_profile
    return ProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        date_of_birth=profile.date_of_birth if profile else None,
        show_birthday=profile.show_birthday if profile else True,
        avatar_url=profile.avatar_url if profile else None,
        created_at=user.created_at,
    )


@router.patch("/profile", response_model=ProfileResponse, tags=["user"])
async def update_profile(
    payload: ProfileUpdate,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = ProfileService(session)
    await service.update_profile(
        user_id=current_user.id,
        full_name=payload.full_name,
        date_of_birth=payload.date_of_birth,
        show_birthday=payload.show_birthday,
        avatar_url=payload.avatar_url,
    )
    # Перезагружаем пользователя с профилем
    user = await service.get_profile(current_user.id)
    profile = user.user_profile
    return ProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        date_of_birth=profile.date_of_birth if profile else None,
        show_birthday=profile.show_birthday if profile else True,
        avatar_url=profile.avatar_url if profile else None,
        created_at=user.created_at,
    )


# Встроенный мессенджер
@router.post("/direct-messages", response_model=DirectMessageResponse, status_code=status.HTTP_201_CREATED, tags=["user"])
async def send_direct_message(
    payload: DirectMessageCreate,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = DirectMessageService(session)
    message = await service.send_message(
        sender_id=current_user.id,
        recipient_id=payload.recipient_id,
        content=payload.content,
    )
    return DirectMessageResponse(
        id=message.id,
        sender_id=message.sender_id,
        recipient_id=message.recipient_id,
        content=message.content,
        read=message.read,
        created_at=message.created_at,
    )


@router.get("/direct-messages/conversation/{user_id}", response_model=DirectMessageList, tags=["user"])
async def get_conversation(
    user_id: UUID,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = DirectMessageService(session)
    messages = await service.get_conversation(user1_id=current_user.id, user2_id=user_id)
    return DirectMessageList(
        items=[
            DirectMessageResponse(
                id=m.id,
                sender_id=m.sender_id,
                recipient_id=m.recipient_id,
                content=m.content,
                read=m.read,
                created_at=m.created_at,
            )
            for m in messages
        ]
    )


@router.get("/direct-messages/unread-count", tags=["user"])
async def get_unread_count(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = DirectMessageService(session)
    count = await service.get_unread_count(current_user.id)
    return {"unread_count": count}


# Одногруппники
@router.get("/students/classmates", response_model=ClassmatesList, tags=["student"])
async def get_classmates(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from sqlalchemy import select

    from edutrack.infrastructure.db.models import Student

    # Получаем профиль студента
    stmt = select(Student).where(Student.user_id == current_user.id)
    student = await session.scalar(stmt)
    if not student:
        return ClassmatesList(items=[])

    service = ClassmatesService(session)
    classmates = await service.get_classmates(student.id)

    items = []
    for classmate in classmates:
        user = classmate.user
        profile = user.user_profile
        items.append(
            ClassmateResponse(
                user_id=user.id,
                full_name=user.full_name,
                avatar_url=profile.avatar_url if profile else None,
                date_of_birth=profile.date_of_birth if profile and profile.show_birthday else None,
                show_birthday=profile.show_birthday if profile else True,
            )
        )

    return ClassmatesList(items=items)


# Новости
@router.post("/news", response_model=NewsResponse, status_code=status.HTTP_201_CREATED, tags=["staff"])
async def create_news(
    payload: NewsCreate,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    _user=Depends(require_staff),
):
    service = NewsService(session)
    news_item = await service.create_news(
        school_id=payload.school_id,
        author_id=current_user.id,
        title=payload.title,
        content=payload.content,
        preview_image_url=payload.preview_image_url,
        published_at=payload.published_at,
    )
    # Получаем автора для имени
    from edutrack.infrastructure.repositories.sqlalchemy import SqlAlchemyUserRepository
    user_repo = SqlAlchemyUserRepository(session)
    author = await user_repo.get_by_id(current_user.id)

    return NewsResponse(
        id=news_item.id,
        school_id=news_item.school_id,
        author_id=news_item.author_id,
        author_name=author.full_name if author else "Неизвестно",
        title=news_item.title,
        content=news_item.content,
        preview_image_url=news_item.preview_image_url,
        published_at=news_item.published_at,
        created_at=news_item.created_at,
    )


@router.get("/news/preview", response_model=NewsPreviewList, tags=["user"])
async def get_news_preview(
    school_id: UUID | None = None,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    service = NewsService(session)
    news_items = await service.get_preview_list(school_id=school_id, limit=limit)
    return NewsPreviewList(
        items=[
            NewsPreview(
                id=item.id,
                title=item.title,
                preview_image_url=item.preview_image_url,
                published_at=item.published_at,
            )
            for item in news_items
        ]
    )


@router.get("/news/{news_id}", response_model=NewsResponse, tags=["user"])
async def get_news(
    news_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    service = NewsService(session)
    news_item = await service.get_news(news_id)

    # Получаем автора для имени
    from edutrack.infrastructure.repositories.sqlalchemy import SqlAlchemyUserRepository
    user_repo = SqlAlchemyUserRepository(session)
    author = await user_repo.get_by_id(news_item.author_id)

    return NewsResponse(
        id=news_item.id,
        school_id=news_item.school_id,
        author_id=news_item.author_id,
        author_name=author.full_name if author else "Неизвестно",
        title=news_item.title,
        content=news_item.content,
        preview_image_url=news_item.preview_image_url,
        published_at=news_item.published_at,
        created_at=news_item.created_at,
    )


# Промежуточная аттестация
@router.get("/students/{student_id}/interim-assessments", response_model=InterimAssessmentList, tags=["student", "guardian"])
async def get_interim_assessments(
    student_id: UUID,
    school_year: int | None = None,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # Проверяем доступ: студент может видеть только свои оценки, родитель - своих детей
    from sqlalchemy import select

    from edutrack.infrastructure.db.models import Guardian, Student, StudentGuardian

    # Проверяем, является ли пользователь студентом
    stmt = select(Student).where(Student.user_id == current_user.id)
    current_student = await session.scalar(stmt)

    # Проверяем, является ли пользователь родителем этого студента
    if current_student and current_student.id == student_id:
        pass  # Доступ разрешен
    else:
        # Проверяем, является ли пользователь родителем
        stmt = select(Guardian).where(Guardian.user_id == current_user.id)
        guardian = await session.scalar(stmt)
        if guardian:
            stmt = select(StudentGuardian).where(
                StudentGuardian.student_id == student_id,
                StudentGuardian.guardian_id == guardian.id
            )
            guardian_link = await session.scalar(stmt)
            if not guardian_link:
                from fastapi import HTTPException
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещен")
        else:
            from fastapi import HTTPException
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещен")

    service = InterimAssessmentService(session)
    assessments = await service.get_by_student(student_id, school_year)

    # Получаем названия предметов
    from edutrack.infrastructure.db.models import Subject
    items = []
    for assessment in assessments:
        stmt = select(Subject).where(Subject.id == assessment.subject_id)
        subject = await session.scalar(stmt)

        items.append(
            InterimAssessmentResponse(
                id=assessment.id,
                student_id=assessment.student_id,
                subject_id=assessment.subject_id,
                subject_name=subject.name if subject else "Неизвестный предмет",
                school_year=assessment.school_year,
                semester=assessment.semester,
                grade=assessment.grade,
                comment=assessment.comment,
                created_at=assessment.created_at,
            )
        )

    return InterimAssessmentList(items=items)


# Успеваемость
@router.get("/students/{student_id}/performance/{year}/{month}", response_model=PerformanceResponse, tags=["student", "guardian"])
async def get_performance(
    student_id: UUID,
    year: int,
    month: int,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # Проверяем доступ (аналогично промежуточной аттестации)
    from fastapi import HTTPException
    from sqlalchemy import select

    from edutrack.infrastructure.db.models import Guardian, Student, StudentGuardian

    stmt = select(Student).where(Student.user_id == current_user.id)
    current_student = await session.scalar(stmt)

    if current_student and current_student.id == student_id:
        pass
    else:
        stmt = select(Guardian).where(Guardian.user_id == current_user.id)
        guardian = await session.scalar(stmt)
        if guardian:
            stmt = select(StudentGuardian).where(
                StudentGuardian.student_id == student_id,
                StudentGuardian.guardian_id == guardian.id
            )
            guardian_link = await session.scalar(stmt)
            if not guardian_link:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещен")
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещен")

    service = PerformanceService(session)
    statistics = await service.get_performance(student_id, month, year)

    # Получаем названия предметов
    from edutrack.infrastructure.db.models import Subject
    result_items = []
    for stat in statistics:
        stmt = select(Subject).where(Subject.id == stat["subject_id"])
        subject = await session.scalar(stmt)

        result_items.append(
            GradeStatistics(
                subject_id=stat["subject_id"],
                subject_name=subject.name if subject else "Неизвестный предмет",
                grade_count=stat["grade_count"],
                average_grade=stat["average_grade"],
                grades=stat["grades"],
            )
        )

    return PerformanceResponse(month=month, year=year, statistics=result_items)
