"""Общие патчи для тестов."""
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch


@contextmanager
def patch_smtp_settings(port=587, use_tls=True):
    """Патч для настроек SMTP."""
    with patch("edutrack.infrastructure.email.sender.get_settings") as mock_settings:
        mock_settings.return_value.smtp_from = "test@example.com"
        mock_settings.return_value.smtp_port = port
        mock_settings.return_value.smtp_use_tls = use_tls
        mock_settings.return_value.smtp_host = "smtp.example.com"
        mock_settings.return_value.smtp_user = "user"
        mock_settings.return_value.smtp_password = "pass"
        yield mock_settings


@contextmanager
def patch_send_email():
    """Патч для send_email функции."""
    with patch("edutrack.application.password_reset.send_email", new_callable=AsyncMock) as mock:
        yield mock


@contextmanager
def patch_cache(cache_hit=False, cache_data=None):
    """Патч для функций кэширования."""
    cache_set_calls = []
    invalidate_calls = []

    async def fake_get_cache(key):
        return cache_data if cache_hit else None

    async def fake_set_cache(key, value, ttl_seconds):
        cache_set_calls.append({"key": key, "value": value, "ttl": ttl_seconds})

    async def fake_invalidate(key):
        invalidate_calls.append(key)

    # Патчим в разных модулях
    with patch("edutrack.application.grades.get_cache", side_effect=fake_get_cache), \
         patch("edutrack.application.grades.set_cache", side_effect=fake_set_cache), \
         patch("edutrack.application.grades.invalidate", side_effect=fake_invalidate), \
         patch("edutrack.application.schools.get_cache", side_effect=fake_get_cache), \
         patch("edutrack.application.schools.set_cache", side_effect=fake_set_cache), \
         patch("edutrack.application.schools.invalidate", side_effect=fake_invalidate), \
         patch("edutrack.application.lessons.get_cache", side_effect=fake_get_cache), \
         patch("edutrack.application.lessons.set_cache", side_effect=fake_set_cache), \
         patch("edutrack.application.lessons.invalidate", side_effect=fake_invalidate):
        yield {
            "get_cache": fake_get_cache,
            "set_cache": fake_set_cache,
            "invalidate": fake_invalidate,
            "set_calls": cache_set_calls,
            "invalidate_calls": invalidate_calls,
        }

