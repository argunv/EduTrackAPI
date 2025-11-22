from collections.abc import Sequence
from email.message import EmailMessage

from aiosmtplib import SMTP

from edutrack.config.settings import get_settings

settings = get_settings()


async def send_email(recipients: Sequence[str], subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(body)

    smtp = SMTP(
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        use_tls=settings.smtp_use_tls,
        username=settings.smtp_user,
        password=settings.smtp_password,
    )
    await smtp.connect()
    try:
        await smtp.send_message(msg)
    finally:
        await smtp.quit()
