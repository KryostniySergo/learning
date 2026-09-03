from fastapi import APIRouter
from pydantic import EmailStr

from app.schemas.account import CheckAccountResponse
from app.schemas.auth import (
    SignUpCompleteRequest,
    SignUpCompleteResponse,
    SignUpRequest,
    SignUpResponse,
)
from app.services.auth_service import AuthService
from app.uow import UnitOfWork

router = APIRouter(tags=["auth"])


@router.get("/check_account/{account}", response_model=CheckAccountResponse)
async def check_account(account: EmailStr) -> CheckAccountResponse:
    """Проверяет, свободна ли почта, и запускает первый шаг регистрации.

    Если почта свободна — создаёт Account и Invite, 'отправляет' код на почту.

    Args:
        account (EmailStr): почта, которую нужно проверить.

    Returns:
        CheckAccountResponse: available=True, если почта свободна и инвайт создан,
            available=False, если почта уже занята.
    """
    async with UnitOfWork() as uow:
        available = await AuthService(uow).check_account(account)
    return CheckAccountResponse(available=available)


@router.post("/sign-up/", response_model=SignUpResponse)
async def sign_up(body: SignUpRequest) -> SignUpResponse:
    """Подтверждает владение почтой по токену инвайта (шаг 2 регистрации).

    Args:
        body (SignUpRequest): почта и токен инвайта, полученный на шаге 1.

    Returns:
        SignUpResponse: confirmed=True при успешном подтверждении.
    """
    async with UnitOfWork() as uow:
        await AuthService(uow).sign_up(body.account, body.invite_token)
    return SignUpResponse(confirmed=True)


@router.post("/sign-up-complete/", response_model=SignUpCompleteResponse)
async def sign_up_complete(body: SignUpCompleteRequest) -> SignUpCompleteResponse:
    """Завершает регистрацию компании (шаг 3).

    Создаёт компанию и сотрудника-администратора этой компании.

    Args:
        body (SignUpCompleteRequest): почта, пароль, имя, фамилия и название компании.

    Returns:
        SignUpCompleteResponse: id созданных компании и пользователя.
    """
    async with UnitOfWork() as uow:
        company_id, user_id = await AuthService(uow).sign_up_complete(
            email=body.account,
            password=body.password,
            first_name=body.first_name,
            last_name=body.last_name,
            company_name=body.company_name,
        )
    return SignUpCompleteResponse(company_id=company_id, user_id=user_id)
