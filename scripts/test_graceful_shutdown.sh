#!/bin/bash

# Скрипт для тестирования graceful shutdown
# Тестирует корректное завершение работы API и Notifier сервисов

set -e

echo "=========================================="
echo "Тестирование Graceful Shutdown"
echo "=========================================="
echo ""

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Функция для проверки логов
check_logs() {
    local service=$1
    local expected_message=$2
    
    echo -e "${YELLOW}Проверка логов сервиса $service...${NC}"
    
    if docker-compose logs --tail=50 "$service" | grep -q "$expected_message"; then
        echo -e "${GREEN}✓ Найдено сообщение: '$expected_message'${NC}"
        return 0
    else
        echo -e "${RED}✗ Сообщение '$expected_message' не найдено в логах${NC}"
        return 1
    fi
}

# Запускаем сервисы
echo -e "${YELLOW}1. Запуск сервисов...${NC}"
docker-compose up -d api notifier

# Ждем, пока сервисы запустятся
echo -e "${YELLOW}2. Ожидание запуска сервисов (10 секунд)...${NC}"
sleep 10

# Проверяем, что сервисы работают
if ! docker-compose ps | grep -q "api.*Up"; then
    echo -e "${RED}✗ API сервис не запущен${NC}"
    exit 1
fi

if ! docker-compose ps | grep -q "notifier.*Up"; then
    echo -e "${RED}✗ Notifier сервис не запущен${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Сервисы запущены${NC}"
echo ""

# Тест 1: Graceful shutdown API через docker-compose stop
echo -e "${YELLOW}3. Тест 1: Graceful shutdown API через docker-compose stop...${NC}"
docker-compose stop -t 30 api

# Проверяем логи API
echo ""
echo -e "${YELLOW}Проверка логов API...${NC}"
if check_logs api "Начало graceful shutdown"; then
    echo -e "${GREEN}✓ API: Найдено сообщение о начале shutdown${NC}"
else
    echo -e "${RED}✗ API: Сообщение о начале shutdown не найдено${NC}"
fi

if check_logs api "Redis соединения закрыты"; then
    echo -e "${GREEN}✓ API: Redis соединения закрыты${NC}"
else
    echo -e "${YELLOW}⚠ API: Сообщение о закрытии Redis не найдено (может быть нормально, если Redis не использовался)${NC}"
fi

if check_logs api "Соединения с БД закрыты"; then
    echo -e "${GREEN}✓ API: Соединения с БД закрыты${NC}"
else
    echo -e "${YELLOW}⚠ API: Сообщение о закрытии БД не найдено${NC}"
fi

echo ""

# Перезапускаем API для следующего теста
echo -e "${YELLOW}4. Перезапуск API...${NC}"
docker-compose up -d api
sleep 5

# Тест 2: Graceful shutdown через SIGTERM
echo -e "${YELLOW}5. Тест 2: Graceful shutdown API через SIGTERM...${NC}"
API_PID=$(docker-compose exec -T api pgrep -f "uvicorn" || echo "")
if [ -n "$API_PID" ]; then
    docker-compose exec -T api kill -TERM "$API_PID"
    sleep 5
    echo -e "${GREEN}✓ SIGTERM отправлен${NC}"
else
    echo -e "${YELLOW}⚠ PID процесса не найден, пропускаем тест${NC}"
fi

echo ""

# Тест 3: Graceful shutdown Notifier
echo -e "${YELLOW}6. Тест 3: Graceful shutdown Notifier...${NC}"
docker-compose stop -t 30 notifier

# Проверяем логи Notifier
echo ""
echo -e "${YELLOW}Проверка логов Notifier...${NC}"
if check_logs notifier "Начало graceful shutdown notifier"; then
    echo -e "${GREEN}✓ Notifier: Найдено сообщение о начале shutdown${NC}"
else
    echo -e "${RED}✗ Notifier: Сообщение о начале shutdown не найдено${NC}"
fi

if check_logs notifier "RabbitMQ соединение закрыто"; then
    echo -e "${GREEN}✓ Notifier: RabbitMQ соединение закрыто${NC}"
else
    echo -e "${YELLOW}⚠ Notifier: Сообщение о закрытии RabbitMQ не найдено${NC}"
fi

if check_logs notifier "Соединения с БД закрыты"; then
    echo -e "${GREEN}✓ Notifier: Соединения с БД закрыты${NC}"
else
    echo -e "${YELLOW}⚠ Notifier: Сообщение о закрытии БД не найдено${NC}"
fi

if check_logs notifier "Graceful shutdown notifier завершен"; then
    echo -e "${GREEN}✓ Notifier: Graceful shutdown завершен${NC}"
else
    echo -e "${YELLOW}⚠ Notifier: Финальное сообщение о завершении не найдено${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Тестирование завершено!${NC}"
echo "=========================================="
echo ""
echo "Для просмотра полных логов используйте:"
echo "  docker-compose logs api"
echo "  docker-compose logs notifier"

