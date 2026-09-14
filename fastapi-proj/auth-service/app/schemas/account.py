from pydantic import BaseModel


class CheckAccountResponse(BaseModel):
    """Ответ на проверку доступности аккаунта."""

    available: bool
