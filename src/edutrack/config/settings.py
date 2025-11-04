from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "EduTrack API"
    environment: str = Field(default="dev")
    debug: bool = Field(default=False)

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://edutrack:edutrack@postgres:5432/edutrack", env="DATABASE_URL"
    )

    # Redis
    redis_url: str = Field(default="redis://redis:6379/0", env="REDIS_URL")

    # RabbitMQ
    rabbitmq_url: str = Field(default="amqp://guest:guest@rabbitmq:5672/", env="RABBITMQ_URL")
    rabbitmq_email_queue: str = Field(default="email.send")

    # Auth
    jwt_secret: str = Field(default="changeme", env="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256")
    jwt_exp_minutes: int = Field(default=60)

    # SMTP
    smtp_host: str = Field(default="smtp.example.com", env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_user: str = Field(default="user", env="SMTP_USER")
    smtp_password: str = Field(default="password", env="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, env="SMTP_USE_TLS")
    smtp_from: str = Field(default="noreply@edutrack.local")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()

