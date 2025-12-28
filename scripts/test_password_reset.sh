#!/bin/bash
# Скрипт для тестирования восстановления пароля

set -e

API_URL="http://127.0.0.1:8000/api/v1"

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "============================================================"
echo "Тестирование восстановления пароля"
echo "============================================================"
echo ""

# Проверяем, передан ли токен
if [ -z "$1" ]; then
    echo -e "${YELLOW}Использование:${NC}"
    echo "  $0 <token> [new_password]"
    echo ""
    echo "Пример:"
    echo "  $0 eheqZ--s_Ifk_0SWPEd5zPwiG_8WXObNV63f39AEiP8 newpassword123"
    echo ""
    echo "Или используйте токен из письма:"
    echo "  $0 'eheqZ--s_Ifk_0SWPEd5zPwiG_8WXObNV63f39AEiP8'"
    exit 1
fi

TOKEN=$1
NEW_PASSWORD=${2:-"newpassword123"}

echo -e "${GREEN}Токен:${NC} $TOKEN"
echo -e "${GREEN}Новый пароль:${NC} $NEW_PASSWORD"
echo ""

# Отправляем запрос на восстановление пароля
echo "Отправка запроса на восстановление пароля..."
RESPONSE=$(curl -s -X POST "$API_URL/auth/password-reset/confirm" \
  -H "Content-Type: application/json" \
  -d "{
    \"token\": \"$TOKEN\",
    \"new_password\": \"$NEW_PASSWORD\"
  }")

# Проверяем ответ
if echo "$RESPONSE" | grep -q "успешно изменен\|successfully"; then
    echo -e "${GREEN}✓ Пароль успешно изменен!${NC}"
    echo ""
    echo "Теперь вы можете войти с новым паролем:"
    echo "  Email: v_argun@inbox.ru"
    echo "  Пароль: $NEW_PASSWORD"
    echo ""
    echo "Для входа используйте:"
    echo "  curl -X POST $API_URL/auth/login \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"email\": \"v_argun@inbox.ru\", \"password\": \"$NEW_PASSWORD\"}'"
else
    echo -e "${RED}❌ Ошибка при восстановлении пароля${NC}"
    echo "Ответ сервера: $RESPONSE"
    echo ""
    echo "Возможные причины:"
    echo "  - Токен недействителен или истек"
    echo "  - Токен уже был использован"
    echo "  - Сервер недоступен"
    exit 1
fi

