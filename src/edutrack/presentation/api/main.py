import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware

from edutrack.application.health import check_health
from edutrack.config.settings import get_settings
from edutrack.infrastructure.cache.redis import close_redis
from edutrack.infrastructure.db.database import engine, get_session
from edutrack.infrastructure.db.models import UserRole
from edutrack.presentation.api.routes.v1 import router as v1_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("edutrack.api")
settings = get_settings()

# Маппинг тегов к требуемым ролям
TAG_ROLES = {
    "admin": [
        UserRole.admin,
        UserRole.director,
        UserRole.deputy_director,
    ],
    "staff": [
        UserRole.admin,
        UserRole.director,
        UserRole.deputy_director,
        UserRole.head_teacher,
        UserRole.teacher,
        UserRole.class_teacher,
        UserRole.subject_teacher,
        UserRole.methodist,
        UserRole.scheduler,
    ],
    "user": [
        UserRole.admin,
        UserRole.director,
        UserRole.deputy_director,
        UserRole.head_teacher,
        UserRole.teacher,
        UserRole.class_teacher,
        UserRole.subject_teacher,
        UserRole.methodist,
        UserRole.scheduler,
        UserRole.psychologist,
        UserRole.librarian,
        UserRole.secretary,
        UserRole.student,
        UserRole.guardian,
    ],
    "auth": [],  # Публичные эндпоинты
}


def has_access(user_roles: list[UserRole], required_roles: list[UserRole]) -> bool:
    """Проверяет, имеет ли пользователь доступ к эндпоинту (хотя бы одна роль должна совпадать)."""
    if not required_roles:
        return True  # Публичный эндпоинт
    if not user_roles:
        return False
    return any(role in required_roles for role in user_roles)


def custom_openapi(app: FastAPI, request: Request | None = None) -> dict[str, Any]:
    """Кастомная генерация OpenAPI схемы с фильтрацией по ролям."""
    # Кэшируем базовую схему
    cache_key = "base_schema"
    if not hasattr(app.state, cache_key):
        base_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        # Добавляем информацию о безопасности
        base_schema["components"]["securitySchemes"] = {
            "Bearer": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Введите токен в формате: Bearer <token>",
            }
        }

        # Добавляем информацию о требуемых ролях в описания эндпоинтов
        for path_item in base_schema.get("paths", {}).values():
            for operation in path_item.values():
                if not isinstance(operation, dict):
                    continue

                tags = operation.get("tags", [])
                required_roles = []
                for tag in tags:
                    if tag in TAG_ROLES:
                        required_roles.extend(TAG_ROLES[tag])

                # Сохраняем требуемые роли в x-required-roles для фильтрации
                if required_roles:
                    operation["x-required-roles"] = [role.value for role in set(required_roles)]
                    role_names = [role.value for role in set(required_roles)]
                    description = operation.get("description", "")
                    role_info = f"\n\n**Требуемые роли:** {', '.join(role_names)}"
                    operation["description"] = description + role_info if description else role_info.strip()

                # Добавляем security к операциям, которые требуют авторизации
                if tags and "auth" not in tags:
                    operation["security"] = [{"Bearer": []}]

        setattr(app.state, cache_key, base_schema)

    base_schema = getattr(app.state, cache_key).copy()

    # Если есть request, фильтруем эндпоинты по ролям пользователя
    # Примечание: для OpenAPI схемы это упрощенная проверка, реальная проверка в зависимостях
    if request:
        # Для упрощения показываем все эндпоинты, если есть токен
        # Реальная фильтрация происходит в зависимостях при выполнении запроса
        pass

    return base_schema


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware для добавления заголовков безопасности."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Заголовки безопасности
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Удаляем информацию о сервере
        if "server" in response.headers:
            del response.headers["server"]

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware для логирования запросов."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Логируем входящий запрос
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None,
            },
        )

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            # Логируем ответ
            logger.info(
                f"Response: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": f"{process_time:.3f}s",
                },
            )

            # Добавляем время обработки в заголовок
            response.headers["X-Process-Time"] = f"{process_time:.3f}"

            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Error: {request.method} {request.url.path} - {str(e)}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "process_time": f"{process_time:.3f}s",
                },
                exc_info=True,
            )
            raise


async def shutdown_handler() -> None:
    """Обработчик graceful shutdown."""
    logger.info("Начало graceful shutdown...")

    # Закрываем Redis соединения
    try:
        await close_redis()
        logger.info("Redis соединения закрыты")
    except Exception as e:
        logger.error(f"Ошибка при закрытии Redis: {e}", exc_info=True)

    # Закрываем соединения с БД
    try:
        await engine.dispose()
        logger.info("Соединения с БД закрыты")
    except Exception as e:
        logger.error(f"Ошибка при закрытии соединений с БД: {e}", exc_info=True)

    logger.info("Graceful shutdown завершен")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler для управления жизненным циклом приложения.
    Выполняет graceful shutdown при остановке приложения.
    """
    # Startup
    logger.info("Приложение запущено")
    yield
    # Shutdown
    await shutdown_handler()


def create_app() -> FastAPI:
    app = FastAPI(
        title="EduTrack API",
        version="1.0.0",
        description="""
        Авторизация

        Для использования API необходимо:
        1. Авторизоваться через /api/v1/auth/login
        2. Получить токен доступа
        3. Использовать токен в заголовке: Authorization: Bearer <token>

        Роли и доступ

        - admin: Полный доступ ко всем эндпоинтам
        - teacher: Доступ к эндпоинтам для работы с уроками, оценками, предметами
        - student/guardian: Доступ к базовым эндпоинтам (сообщения)

        В описании каждого эндпоинта указаны требуемые роли.
        """,
        lifespan=lifespan,
    )

    # CORS middleware
    # Никогда не используем "*" для безопасности
    cors_origins = settings.cors_origins if settings.cors_origins else []
    if not cors_origins and settings.debug:
        logger.warning(
            "CORS origins не настроен. В debug режиме рекомендуется указать конкретные origins. "
            "По умолчанию CORS будет отключен."
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Process-Time"],
    )

    # Security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # Request logging middleware
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(v1_router)

    # Переопределяем генерацию OpenAPI схемы
    app.openapi = lambda: custom_openapi(app, request=None)

    # Обработчик исключений
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error" if not settings.debug else str(exc),
            },
        )

    @app.get("/health")
    async def health(session: AsyncSession = Depends(get_session)):
        status_data = await check_health(session)
        status_code = 200 if status_data["status"] == "ok" else 503
        return JSONResponse(content=status_data, status_code=status_code)

    return app


app = create_app()
