import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)


def generate_avatar_url(name: str, size: int = 200) -> str:
    """
    Генерирует URL аватара из имени пользователя используя UI Avatars API.
    
    UI Avatars - бесплатный сервис, не требует регистрации или API ключа.
    Генерирует аватар с инициалами пользователя.
    
    Args:
        name: Полное имя пользователя (будет использовано для генерации инициалов)
        size: Размер аватара в пикселях (по умолчанию 200)
    
    Returns:
        URL аватара (PNG изображение)
    """
    # Очищаем имя от лишних символов
    clean_name = name.strip()[:100]  # Ограничиваем длину
    encoded_name = quote(clean_name)
    
    # UI Avatars API - бесплатный, не требует регистрации
    # Формат: https://ui-avatars.com/api/?name={name}&size={size}
    avatar_url = f"https://ui-avatars.com/api/?name={encoded_name}&size={size}"
    
    logger.debug(f"Сгенерирован URL аватара для '{name}' (размер: {size}px)")
    return avatar_url

