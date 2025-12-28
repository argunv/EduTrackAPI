"""Вспомогательные функции для проверок в тестах."""
import pytest
from fastapi import HTTPException


def assert_http_exception(func, status_code, detail_contains=None):
    """Проверяет, что функция вызывает HTTPException с указанным кодом."""
    with pytest.raises(HTTPException) as exc_info:
        func()

    assert exc_info.value.status_code == status_code
    if detail_contains:
        assert detail_contains.lower() in exc_info.value.detail.lower()

    return exc_info.value


async def assert_http_exception_async(coro, status_code, detail_contains=None):
    """Проверяет, что корутина вызывает HTTPException с указанным кодом."""
    with pytest.raises(HTTPException) as exc_info:
        await coro

    assert exc_info.value.status_code == status_code
    if detail_contains:
        assert detail_contains.lower() in exc_info.value.detail.lower()

    return exc_info.value

