from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    jwt_secret: str = "changeme"
    jwt_algorithm: str = "HS256"
    jwt_exp_minutes: int = 60

    # SMTP
    smtp_host: str = "smtp.example.com"
    smtp_port: int = 587
    smtp_user: str = "user"
    smtp_password: str = "password"
    smtp_use_tls: bool = True
    smtp_from: str = "noreply@edutrack.local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
