from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.schemas.auth import (
    ChangeEmailRequest,
    ConfirmEmailRequest,
    ProfileResponse,
    UpdateProfileRequest,
)
from app.schemas.current_user import CurrentUser
from app.services.mail_service import MailService
from app.services.profile_service import ProfileService
from app.uow import UnitOfWork

router = APIRouter(prefix="/me", tags=["profile"])

CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


@router.get("/", response_model=ProfileResponse)
async def get_profile(current_user: CurrentUserDep) -> ProfileResponse:
    """Возвращает личные данные текущего пользователя.

    Args:
        current_user (CurrentUser): контекст текущего пользователя.

    Returns:
        ProfileResponse: имя, фамилия и привязанная почта.
    """
    async with UnitOfWork() as uow:
        user, email = await ProfileService(uow).get_profile(current_user.user_id)
    return ProfileResponse(user_id=user.id, first_name=user.name, last_name=user.surname, email=email)


@router.patch("/", response_model=ProfileResponse)
async def update_profile(body: UpdateProfileRequest, current_user: CurrentUserDep) -> ProfileResponse:
    """Меняет имя и фамилию текущего пользователя.

    Args:
        body (UpdateProfileRequest): новые значения полей.
        current_user (CurrentUser): контекст текущего пользователя.

    Returns:
        ProfileResponse: обновлённые личные данные.
    """
    async with UnitOfWork() as uow:
        service = ProfileService(uow)
        await service.update_name(current_user.user_id, body.first_name, body.last_name)
        user, email = await service.get_profile(current_user.user_id)
    return ProfileResponse(user_id=user.id, first_name=user.name, last_name=user.surname, email=email)


@router.post("/email/", status_code=202)
async def request_email_change(body: ChangeEmailRequest, current_user: CurrentUserDep) -> dict:
    """Запускает смену почты: отправляет код подтверждения на новый адрес.

    Args:
        body (ChangeEmailRequest): новый адрес почты.
        current_user (CurrentUser): контекст текущего пользователя.

    Returns:
        dict: подтверждение отправки письма.
    """
    async with UnitOfWork() as uow:
        token = await ProfileService(uow).request_email_change(current_user.user_id, body.new_account)

    await MailService().send_company_invite(body.new_account, token)
    return {"confirmation_sent": True}


@router.post("/email/confirm/", response_model=ProfileResponse)
async def confirm_email_change(body: ConfirmEmailRequest, current_user: CurrentUserDep) -> ProfileResponse:
    """Подтверждает владение новым адресом и переключает на него вход.

    Args:
        body (ConfirmEmailRequest): токен из письма.
        current_user (CurrentUser): контекст текущего пользователя.

    Returns:
        ProfileResponse: личные данные с обновлённой почтой.
    """
    async with UnitOfWork() as uow:
        service = ProfileService(uow)
        await service.confirm_email_change(current_user.user_id, body.invite_token)
        user, email = await service.get_profile(current_user.user_id)
    return ProfileResponse(user_id=user.id, first_name=user.name, last_name=user.surname, email=email)
