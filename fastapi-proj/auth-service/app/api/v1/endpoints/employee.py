from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_current_user
from app.schemas.auth import (
    CreateEmployeeRequest,
    CreateEmployeeResponse,
    RegisterEmployeeRequest,
    RegisterEmployeeResponse,
)
from app.schemas.current_user import CurrentUser
from app.services.employee_service import EmployeeService
from app.uow import UnitOfWork

router = APIRouter(prefix="/employees", tags=["employees"])

CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


@router.post("/", response_model=CreateEmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    body: CreateEmployeeRequest,
    current_user: CurrentUserDep,
) -> CreateEmployeeResponse:
    """Создаёт сотрудника в компании администратора и высылает ему инвайт.

    Если сотрудник уже зарегистрирован в системе, он просто добавляется
    в компанию администратора — инвайт в этом случае не выпускается.

    Args:
        body (CreateEmployeeRequest): почта, имя и фамилия сотрудника.
        current_user (CurrentUser): контекст администратора.

    Returns:
        CreateEmployeeResponse: id сотрудника и признак отправки инвайта.
    """
    async with UnitOfWork() as uow:
        employee_id, token = await EmployeeService(uow).create_employee(
            email=body.account,
            first_name=body.first_name,
            last_name=body.last_name,
            current_user=current_user,
        )
    return CreateEmployeeResponse(employee_id=employee_id, invite_sent=token is not None)


@router.post("/register/", response_model=RegisterEmployeeResponse)
async def register_employee(body: RegisterEmployeeRequest) -> RegisterEmployeeResponse:
    """Завершает регистрацию сотрудника по ссылке из письма.

    Args:
        body (RegisterEmployeeRequest): токен инвайта и задаваемый пароль.

    Returns:
        RegisterEmployeeResponse: id зарегистрированного сотрудника.
    """
    async with UnitOfWork() as uow:
        employee_id = await EmployeeService(uow).register_employee(body.invite_token, body.password)
    return RegisterEmployeeResponse(employee_id=employee_id)
