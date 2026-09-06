import logging
from email.message import EmailMessage

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailSender:
    """Отправка писем через SMTP.

    В учебном окружении письма уходят в MailHog, где их видно
    в веб-интерфейсе — реальная доставка не производится.
    """

    async def send(self, to: str, subject: str, body: str) -> None:
        """Отправляет письмо получателю.

        Ошибка отправки логируется, но не пробрасывается наверх: недоступность
        почтового сервера не должна отменять уже совершённую регистрацию.

        Args:
            to (str): адрес получателя.
            subject (str): тема письма.
            body (str): текст письма.
        """
        message = EmailMessage()
        message["From"] = settings.smtp_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                start_tls=False,
            )
            logger.info("email sent to %s: %s", to, subject)
        except Exception:
            logger.exception("failed to send email to %s", to)
