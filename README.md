# EduTrack API

Производственный бэкенд электронного дневника на FastAPI, PostgreSQL, Redis и RabbitMQ. Проект включает REST API и сервис-рассылку notifier.

## Требования
- Python 3.11+
- Docker / docker-compose
- Poetry

## Запуск
1. Скопировать `env.example` в `.env` и заполнить обязательные параметры:
   - **JWT_SECRET** (обязательно, минимум 32 символа) — секретный ключ для JWT токенов
   - **CORS_ORIGINS** (опционально) — список разрешенных origins для CORS (например: `[http://localhost:3000,https://app.example.com]`)
   - SMTP настройки для отправки email
2. Создать виртуальное окружение `python3.x -m venv venv`
3. Активировать виртуальное окружение `source venv/bin/activate`
4. Установить `poetry`: `pip install poetry`
5. Установить зависимости с помощью poetry `poetry install`
6. Установите утилиту `task` для удобной работы с проектом.
7. `task up` — поднимет Postgres, Redis, RabbitMQ, API и notifier.
8. `task db:migrate` — применить миграции базы данных.
9. `task load-demo` — загрузить демонстрационные данные (опционально).
10. `task create-superuser` — создать суперпользователя для полного доступа к API.
11. Swagger: `http://127.0.0.1:8000/docs`

## Тесты
```bash
poetry run pytest --cov=edutrack
```

Или через task:
```bash
task test
```

## Проверка качества кода

### Линтеры
```bash
task lint          # Запустить все линтеры (ruff, flake8, mypy)
task lint-fix      # Автоматически исправить проблемы
```

### Безопасность
```bash
task security      # Проверить безопасность кода (bandit, safety)
```

### Полная проверка (CI)
```bash
task ci            # Запустить все проверки (линтеры, тесты, безопасность)
```

### Тестирование Graceful Shutdown
```bash
./scripts/test_graceful_shutdown.sh  # Автоматический тест
```

Подробнее см. `scripts/test_graceful_shutdown_manual.md`

## Сервисы
- `api` — FastAPI `/api/v1`, Swagger `/docs`, health `/health`
- `notifier` — consumer очереди `email.send`, отправляет письма через SMTP
- `migrator` — отдельный профиль alembic

## Кеш/очереди
- **Redis**: справочники (schools/classes/subjects), расписание, списки оценок с TTL и инвалидацией.
  - Graceful degradation: приложение продолжает работать при недоступности Redis
  - Connection pool для лучшей производительности
  - Автоматическое удаление поврежденных ключей
- **RabbitMQ**: очередь `email.send`, outbox таблица `email_outbox`.
  - Переиспользование соединений для эффективности
  - Автоматическое переподключение при ошибках
  - Retry логика в notifier (3 попытки с экспоненциальной задержкой)

## Taskfile

Основные команды:
- `task up` — поднять все сервисы
- `task down` — остановить сервисы (graceful shutdown)
- `task db:migrate` — применить миграции
- `task test` — запустить тесты
- `task logs` — показать логи API и notifier
- `task lint` — запустить линтеры (ruff, flake8, mypy)
- `task lint-fix` — автоматически исправить проблемы линтеров
- `task security` — проверить безопасность (bandit, safety)
- `task ci` — полная проверка (линтеры + тесты + безопасность)
- `task create-superuser` — создать суперпользователя
- `task load-demo` — загрузить демонстрационные данные
- `task demo:email` — запустить демонстрацию email сервисов

Полный список: `task up|down|db:migrate|test|logs|save-logs|clear-logs|lint|lint-fix|security|ci|create-superuser|load-demo|demo:email`

## Демонстрация

### Демонстрационные данные
Для загрузки демонстрационных данных (пользователи, школы, классы и т.д.):
```bash
task load-demo
```

### Демонстрация email сервисов
Комплексное тестирование всех email сервисов (отправка сообщений, восстановление пароля и т.д.):
```bash
task demo:email
```

Подробнее см. `scripts/demo/README.md`

## Архитектура и особенности реализации

### Graceful Shutdown
- **API**: Использует FastAPI lifespan events для корректного закрытия соединений с Redis и БД
- **Notifier**: Ожидает завершения активных задач (до 30 секунд) перед остановкой
- Все соединения закрываются корректно при получении SIGTERM/SIGINT

### Генерация аватаров
- Автоматическая генерация аватаров для новых пользователей через [UI Avatars API](https://ui-avatars.com)
- Не требует регистрации или API ключей
- Генерирует аватар с инициалами на основе имени пользователя

### Обработка ошибок
- **Redis**: Все операции кеширования обрабатывают ошибки gracefully
- **RabbitMQ**: Ошибки публикации обрабатываются, outbox помечается как failed
- **Email**: Конкретные типы исключений SMTP с детальным логированием
- **Notifier**: Retry логика с экспоненциальной задержкой (3 попытки)

### Безопасность
- **JWT Secret**: Обязательная валидация минимум 32 символа при старте
- **CORS**: Никогда не разрешает `"*"`, даже в debug режиме
- Все внешние вызовы имеют graceful degradation

## Переменные окружения

Обязательные:
- `JWT_SECRET` — секретный ключ для JWT (минимум 32 символа)

Опциональные:
- `CORS_ORIGINS` — список разрешенных origins (формат: `[http://localhost:3000,https://app.example.com]`)
- `UNSPLASH_ACCESS_KEY` — больше не используется (заменено на UI Avatars)

Полный список см. в `env.example`
