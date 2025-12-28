# EduTrack API

Производственный бэкенд электронного дневника на FastAPI, PostgreSQL, Redis и RabbitMQ. Проект включает REST API и сервис-рассылку notifier.

## Требования
- Python 3.11+
- Docker / docker-compose
- Poetry

## Запуск
1. Скопировать `env.example` в `.env` и заполнить SMTP/секреты.
2. Создать виртуальное окружение `python3.x -m venv venv`
3. Активировать виртуальное окружение `source venv/bin/activate`
4. Установить `poetry`: `pip install poetry`
5. Установить зависимости с помощью poetry `poetry install`
6. Установите утилиту `task` удобной работы с проектом.
7. `task up` — поднимет Postgres, Redis, RabbitMQ, API и notifier.
8. `task create-superuser` — создайте суперпользователя для полного доступа к API.
9. Swagger: `http://127.0.0.1:8000/docs`

## Тесты
```
poetry run pytest --cov=edutrack
```

## Сервисы
- `api` — FastAPI `/api/v1`, Swagger `/docs`, health `/health`
- `notifier` — consumer очереди `email.send`, отправляет письма через SMTP
- `migrator` — отдельный профиль alembic

## Кеш/очереди
- Redis: справочники (schools/classes/subjects), расписание, списки оценок с TTL и инвалидацией.
- RabbitMQ: очередь `email.send`, outbox таблица `email_outbox`.

## Taskfile
- `task up|down|db:migrate|test|logs|save-logs|clear-logs|lint|lint-fix|security|ci|create-superuser`
