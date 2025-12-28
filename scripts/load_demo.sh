#!/bin/sh

echo "Проверяем наличие psql..."
if ! command -v psql > /dev/null; then
  echo "psql не найден. Установите его и попробуйте снова."
  exit 1
fi

echo "psql найден. Проверяем доступность БД..."
PGPASSWORD=edutrack psql -h localhost -p 5432 -U edutrack -d edutrack -c "SELECT 1" > /dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "Не удалось подключиться к БД. Проверьте конфигурацию и попробуйте снова."
  exit 1
fi

echo "БД доступна. Загружаем данные..."
PGPASSWORD=edutrack psql -h localhost -p 5432 -U edutrack -d edutrack -f ./scripts/demo/demo.sql

echo "Данные загружены успешно."
