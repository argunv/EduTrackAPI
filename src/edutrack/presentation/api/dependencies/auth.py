from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from edutrack.config.settings import get_settings
from edutrack.infrastructure.db.database import get_session
from edutrack.infrastructure.db.models import UserRole, UserRoleAssignment
from edutrack.infrastructure.repositories.sqlalchemy import SqlAlchemyUserRepository

security = HTTPBearer()
settings = get_settings()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), session: AsyncSession = Depends(get_session)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        subject: str | None = payload.get("sub")
        if subject is None:
            raise credentials_exception
        user_id = UUID(subject)
    except JWTError as err:
        raise credentials_exception from err

    repo = SqlAlchemyUserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user


async def get_user_roles(
    current_user = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> list[UserRole]:
    """Получает все роли пользователя."""
    stmt = select(UserRoleAssignment.role).where(UserRoleAssignment.user_id == current_user.id)
    result = await session.scalars(stmt)
    return list(result.all())


def require_any_role(*allowed_roles: UserRole) -> Callable:
    """Создает зависимость для проверки, что у пользователя есть хотя бы одна из указанных ролей."""
    async def role_checker(user_roles: list[UserRole] = Depends(get_user_roles)):
        if not any(role in allowed_roles for role in user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required any of: {[role.value for role in allowed_roles]}",
            )
        return user_roles
    return role_checker


def require_all_roles(*required_roles: UserRole) -> Callable:
    """Создает зависимость для проверки, что у пользователя есть все указанные роли."""
    async def role_checker(user_roles: list[UserRole] = Depends(get_user_roles)):
        if not all(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required all of: {[role.value for role in required_roles]}",
            )
        return user_roles
    return role_checker


# Удобные зависимости для часто используемых ролей
# Для обратной совместимости оставляем require_role как алиас для require_any_role
require_role = require_any_role

# Административные роли
require_admin = require_any_role(UserRole.admin, UserRole.director)
require_director = require_any_role(UserRole.director)
require_head_teacher = require_any_role(UserRole.head_teacher, UserRole.director, UserRole.deputy_director)

# Педагогические роли
require_teacher = require_any_role(
    UserRole.teacher,
    UserRole.class_teacher,
    UserRole.subject_teacher,
    UserRole.head_teacher,
    UserRole.director,
    UserRole.deputy_director,
    UserRole.admin,
)
require_staff = require_any_role(
    UserRole.teacher,
    UserRole.class_teacher,
    UserRole.subject_teacher,
    UserRole.head_teacher,
    UserRole.director,
    UserRole.deputy_director,
    UserRole.methodist,
    UserRole.scheduler,
    UserRole.admin,
)
