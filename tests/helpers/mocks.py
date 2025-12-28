"""Общие моки для тестов."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


class DummySession:
    """Простая мок-сессия для тестов."""

    def __init__(self):
        self.committed = False
        self.rolled_back = False
        self.added = []
        self.deleted = []

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def flush(self):
        pass

    async def execute(self, *args, **kwargs):
        return None

    def add(self, obj):
        self.added.append(obj)

    def delete(self, obj):
        self.deleted.append(obj)


class CacheMocks:
    """Моки для кэширования."""

    @staticmethod
    def create_cache_mocks(cache_hit=False, cache_data=None):
        """Создает моки для get_cache, set_cache, invalidate."""
        cache_set_calls = []
        invalidate_calls = []

        async def fake_get_cache(key):
            return cache_data if cache_hit else None

        async def fake_set_cache(key, value, ttl_seconds):
            cache_set_calls.append({"key": key, "value": value, "ttl": ttl_seconds})

        async def fake_invalidate(key):
            invalidate_calls.append(key)

        return {
            "get_cache": fake_get_cache,
            "set_cache": fake_set_cache,
            "invalidate": fake_invalidate,
            "set_calls": cache_set_calls,
            "invalidate_calls": invalidate_calls,
        }


class SMTPMocks:
    """Моки для SMTP."""

    @staticmethod
    def create_smtp_mock(port=587, use_tls=True, supports_starttls=True):
        """Создает мок SMTP клиента."""
        mock_smtp = AsyncMock()
        mock_smtp.is_ehlo_or_helo_sent = False
        mock_smtp.is_connected = True
        mock_smtp.server_supports = MagicMock(return_value=supports_starttls)
        mock_smtp.send_message = AsyncMock()
        mock_smtp.quit = AsyncMock()
        mock_smtp.ehlo = AsyncMock()
        mock_smtp.starttls = AsyncMock()
        return mock_smtp

    @staticmethod
    def create_smtp_settings(port=587, use_tls=True):
        """Создает мок настроек SMTP."""
        return {
            "smtp_from": "test@example.com",
            "smtp_port": port,
            "smtp_use_tls": use_tls,
            "smtp_host": "smtp.example.com",
            "smtp_user": "user",
            "smtp_password": "pass",
        }


class RepositoryMocks:
    """Базовые моки репозиториев."""

    @staticmethod
    def create_user_repo(users_by_email=None, users_by_id=None):
        """Создает мок UserRepository."""
        users_by_email = users_by_email or {}
        users_by_id = users_by_id or {}

        class UserRepo:
            async def get_by_email(self, email):
                return users_by_email.get(email)

            async def get_by_id(self, user_id):
                return users_by_id.get(user_id)

            async def update_profile(self, user_id, **kwargs):
                user = users_by_id.get(user_id)
                if user:
                    for key, value in kwargs.items():
                        if hasattr(user, key):
                            setattr(user, key, value)
                return user

        return UserRepo()

    @staticmethod
    def create_token_repo(tokens_by_token=None, created_tokens=None):
        """Создает мок PasswordResetTokenRepository."""
        tokens_by_token = tokens_by_token or {}
        created_tokens = created_tokens or []
        mark_as_used_calls = []

        class TokenRepo:
            async def get_by_token(self, token):
                return tokens_by_token.get(token)

            async def create_token(self, user_id, token, expires_at):
                token_obj = SimpleNamespace(
                    id=uuid4(), user_id=user_id, token=token, expires_at=expires_at
                )
                created_tokens.append(token_obj)
                return token_obj

            async def mark_as_used(self, token_id):
                mark_as_used_calls.append(token_id)

        repo = TokenRepo()
        repo.created_tokens = created_tokens
        repo.mark_as_used_calls = mark_as_used_calls
        return repo

    @staticmethod
    def create_message_repo(messages_by_id=None, created_messages=None):
        """Создает мок MessageRepository."""
        messages_by_id = messages_by_id or {}
        created_messages = created_messages or []

        class MessageRepo:
            async def get(self, msg_id):
                return messages_by_id.get(msg_id)

            async def create_message(self, sender_id, subject, body):
                msg = SimpleNamespace(
                    id=uuid4(), sender_id=sender_id, subject=subject, body=body
                )
                created_messages.append(msg)
                return msg

            async def add_recipients(self, message_id, recipients):
                pass

        repo = MessageRepo()
        repo.created_messages = created_messages
        return repo
