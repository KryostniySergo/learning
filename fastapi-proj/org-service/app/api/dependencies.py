from uuid import UUID

from app.schemas.current_user import CurrentUser, Role

# TODO: заменить на реальный разбор JWT, когда в auth-service появится выдача токенов.
# Сейчас возвращает фиктивного администратора, чтобы можно было разрабатывать
# и тестировать сервисный слой до готовности аутентификации.
MOCK_USER_ID = UUID("d8ac40c0-c58a-4817-ada0-23a63a883604")
MOCK_COMPANY_ID = UUID("816764c8-a828-4fb4-b762-4f26815a6fb8")


async def get_current_user() -> CurrentUser:
    """Возвращает контекст текущего пользователя.

    Returns:
        CurrentUser: контекст с user_id, company_id и ролью.
    """
    return CurrentUser(
        user_id=MOCK_USER_ID,
        company_id=MOCK_COMPANY_ID,
        role=Role.ADMIN,
    )
