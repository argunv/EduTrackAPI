"""Конфигурация pytest с фикстурами для тестов."""
import sys
from pathlib import Path

import pytest

# Добавляем tests в путь для импорта
tests_dir = Path(__file__).parent
sys.path.insert(0, str(tests_dir))

from helpers.mocks import DummySession  # noqa: E402


@pytest.fixture
async def session():
    """Фикстура для создания мок-сессии БД."""
    return DummySession()
