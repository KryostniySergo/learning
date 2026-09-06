import logging

from app.adapters.email_sender import EmailSender

logger = logging.getLogger(__name__)


class MailService:
    """Формирует и отправляет письма, предусмотренные флоу регистрации."""

    def __init__(self, sender: EmailSender | None = None) -> None:
        """Инициализирует сервис.

        Args:
            sender (EmailSender | None): отправитель писем. По умолчанию создаётся новый.
        """
        self._sender = sender or EmailSender()

    async def send_company_invite(self, email: str, token: str) -> None:
        """Отправляет код подтверждения при регистрации компании.

        Args:
            email (str): почта получателя.
            token (str): токен инвайта, который нужно ввести на втором шаге.
        """
        body = (
            "Здравствуйте!\n\n"
            "Вы начали регистрацию компании в системе управления бизнесом.\n"
            f"Код подтверждения: {token}\n\n"
            "Если вы не запрашивали регистрацию, просто проигнорируйте это письмо."
        )
        await self._sender.send(email, "Подтверждение регистрации компании", body)

    async def send_employee_invite(self, email: str, token: str) -> None:
        """Отправляет сотруднику ссылку для завершения регистрации.

        Args:
            email (str): почта получателя.
            token (str): токен инвайта для установки пароля.
        """
        body = f"Здравствуйте!\n\nВас добавили в компанию в системе управления бизнесом.\nТокен приглашения: {token}"
        await self._sender.send(email, "Приглашение в компанию", body)
