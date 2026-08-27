from fastapi import APIRouter, HTTPException, status
from pydantic import EmailStr

from app.core.exceptions import (
    InviteAccountMismatchError,
    InviteExpiredError,
    InviteInvalidStatusError,
    InviteNotFoundError,
)
from app.schemas.account import CheckAccountResponse
from app.schemas.auth import SignUpRequest, SignUpResponse
from app.services.auth_service import AccountAlreadyExistsError, AuthService
from app.uow import UnitOfWork

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/api/v1/check_account/{account}", response_model=CheckAccountResponse)
async def check_account(account: EmailStr) -> CheckAccountResponse:
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


@router.post("/api/v1/sign-up/", response_model=SignUpResponse)
async def sign_up(body: SignUpRequest) -> SignUpResponse:
    """Подтверждает владение почтой по токену инвайта (шаг 2 регистрации).

    Args:
        body (SignUpRequest): почта и токен инвайта, полученный на шаге 1.

    Returns:
        SignUpResponse: confirmed=True при успешном подтверждении.

    Raises:
        HTTPException: 404, если инвайт не найден или не относится к этой почте;
            410, если инвайт истёк; 409, если инвайт не в статусе CREATED.
    """
    async with UnitOfWork() as uow:
        service = AuthService(uow)
        try:
            await service.sign_up(body.account, body.invite_token)
        except (InviteNotFoundError, InviteAccountMismatchError) as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invite not found",
            ) from exc
        except InviteExpiredError as exc:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Invite expired",
            ) from exc
        except InviteInvalidStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Invite is not in a valid state for this action",
            ) from exc
        return SignUpResponse(confirmed=True)
