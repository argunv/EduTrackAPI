import logging
from collections.abc import Sequence
from email.message import EmailMessage

from aiosmtplib import (
    SMTP,
    SMTPAuthenticationError,
    SMTPConnectError,
    SMTPDataError,
    SMTPException,
    SMTPRecipientsRefused,
    SMTPServerDisconnected,
    SMTPTimeoutError,
)

from edutrack.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_email(recipients: Sequence[str], subject: str, body: str) -> None:
    """
    Отправить email через SMTP.

    Raises:
        SMTPConnectError: Ошибка подключения к SMTP серверу
        SMTPAuthenticationError: Ошибка аутентификации
        SMTPRecipientsRefused: Ошибка с получателями
        SMTPDataError: Ошибка при отправке данных
        SMTPTimeoutError: Таймаут при отправке
        SMTPServerDisconnected: Разрыв соединения с сервером
        SMTPException: Другие SMTP ошибки
    """
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(body)

    # Для порта 587 используем STARTTLS (сначала обычное соединение, потом TLS)
    # Для порта 465 используем прямое SSL/TLS соединение
    use_tls_direct = settings.smtp_port == 465

    smtp = SMTP(
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        use_tls=use_tls_direct,  # True только для порта 465
        username=settings.smtp_user,
        password=settings.smtp_password,
        timeout=30.0,  # Таймаут 30 секунд
    )

    try:
        await smtp.connect()
    except (SMTPConnectError, SMTPTimeoutError) as e:
        logger.error(f"Ошибка подключения к SMTP серверу {settings.smtp_host}:{settings.smtp_port}: {e}")
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка при подключении к SMTP: {e}", exc_info=True)
        raise SMTPConnectError(f"Неожиданная ошибка подключения: {e}") from e

    # Для порта 587 используем STARTTLS вручную
    # send_message автоматически вызывает login, но STARTTLS нужно вызвать до этого
    if settings.smtp_use_tls and not use_tls_direct:
        try:
            # Проверяем, используется ли уже TLS, чтобы не вызвать starttls дважды
            if not smtp.is_ehlo_or_helo_sent:
                await smtp.ehlo()
            # Проверяем, поддерживает ли сервер STARTTLS и не используется ли уже TLS
            if hasattr(smtp, 'server_supports') and smtp.server_supports('starttls'):
                if not smtp.is_connected or not getattr(smtp, '_tls_established', False):
                    try:
                        await smtp.starttls()
                    except SMTPException as e:
                        logger.warning(f"Ошибка при установке STARTTLS: {e}. Продолжаем без TLS.")
                    except Exception as e:
                        logger.warning(f"Неожиданная ошибка при установке STARTTLS: {e}")
        except SMTPServerDisconnected as e:
            logger.error(f"Соединение с SMTP сервером разорвано при установке TLS: {e}")
            raise
        except Exception as e:
            # Если starttls уже был вызван или не нужен, логируем и продолжаем
            logger.debug(f"STARTTLS не требуется или уже установлен: {e}")

    try:
        await smtp.send_message(msg)
        logger.info(f"Email успешно отправлен получателям: {', '.join(recipients)}")
    except SMTPAuthenticationError as e:
        logger.error(f"Ошибка аутентификации SMTP: {e}")
        raise
    except SMTPRecipientsRefused as e:
        logger.error(f"Получатели отклонены SMTP сервером: {e}")
        raise
    except SMTPDataError as e:
        logger.error(f"Ошибка данных SMTP: {e}")
        raise
    except SMTPTimeoutError as e:
        logger.error(f"Таймаут при отправке email: {e}")
        raise
    except SMTPServerDisconnected as e:
        logger.error(f"Соединение с SMTP сервером разорвано: {e}")
        raise
    except SMTPException as e:
        logger.error(f"SMTP ошибка: {e}")
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка при отправке email: {e}", exc_info=True)
        raise SMTPException(f"Неожиданная ошибка: {e}") from e
    finally:
        try:
            await smtp.quit()
        except (SMTPServerDisconnected, SMTPException) as e:
            logger.warning(f"Ошибка при закрытии SMTP соединения: {e}")
        except Exception as e:
            logger.warning(f"Неожиданная ошибка при закрытии SMTP соединения: {e}")
