from fastapi import APIRouter, HTTPException, status

from app.schemas.account import CheckAccountResponse
from app.services.auth_service import AccountAlreadyExistsError, AuthService
from app.uow import UnitOfWork

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/api/v1/check_account/{account}", response_model=CheckAccountResponse)
async def check_account(account: str) -> CheckAccountResponse:
    """check_account Проверяет, свободна ли почта, и запускает первый шаг регистрации.

    Если почта свободна — создаёт Account и Invite, 'отправляет' код на почту.

    Args:
        account (str): почта, которую нужно проверить.

    Returns:
        CheckAccountResponse: available=True, если почта свободна и инвайт создан,
            available=False, если почта уже занята.

    Raises:
        HTTPException: 409, если почта оказалась занята в момент commit (гонка запросов).
    """
    async with UnitOfWork() as uow:
        service = AuthService(uow)
        try:
            available = await service.check_account(account)
        except AccountAlreadyExistsError as account_already_exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Account already exists",
            ) from account_already_exists
    return CheckAccountResponse(available=available)
