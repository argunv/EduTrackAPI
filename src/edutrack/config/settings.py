import logging
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="",
    )

    app_name: str = "EduTrack API"
    environment: str = "dev"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://edutrack:edutrack@postgres:5432/edutrack"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    rabbitmq_email_queue: str = "email.send"

    # Auth
    jwt_secret: str = Field(..., min_length=32, description="JWT secret key (минимум 32 символа)")
    jwt_algorithm: str = "HS256"
    jwt_exp_minutes: int = 60

    # SMTP
    smtp_host: str = "smtp.example.com"
    smtp_port: int = 587
    smtp_user: str = "user"
    smtp_password: str = "password"
    smtp_use_tls: bool = True
    smtp_from: str = "noreply@edutrack.local"
    
    # CORS
    cors_origins: list[str] = Field(default_factory=list, description="Список разрешенных origins для CORS")

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if not v or v == "changeme":
            raise ValueError(
                "JWT_SECRET должен быть установлен и иметь минимум 32 символа. "
                "Установите переменную окружения JWT_SECRET."
            )
        if len(v) < 32:
            raise ValueError(f"JWT_SECRET слишком короткий ({len(v)} символов). Минимум 32 символа.")
        return v

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: list[str]) -> list[str]:
        if "*" in v:
            logger.warning(
                "CORS origins содержит '*', что небезопасно. "
                "Используйте конкретные домены вместо '*'."
            )
            # Удаляем "*" из списка
            v = [origin for origin in v if origin != "*"]
        return v


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # Дополнительная валидация при старте
    if settings.debug and not settings.cors_origins:
        logger.warning(
            "CORS origins не настроен. В debug режиме рекомендуется указать конкретные origins."
        )
    return settings
