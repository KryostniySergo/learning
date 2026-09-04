from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class SignUpRequest(BaseModel):
    """Тело запроса для шага 2 регистрации — подтверждение владения почтой."""

    account: EmailStr
    invite_token: str


class SignUpResponse(BaseModel):
    """Ответ шага 2 регистрации."""

    confirmed: bool


class SignUpCompleteRequest(BaseModel):
    """Тело запроса для шага 3 регистрации — завершение регистрации компании."""

    account: EmailStr
    password: str = Field(alias="pass")
    first_name: str
    last_name: str
    company_name: str


class SignUpCompleteResponse(BaseModel):
    """Ответ шага 3 регистрации."""

    company_id: UUID
    user_id: UUID


class LoginRequest(BaseModel):
    """Тело запроса на вход в систему."""

    account: EmailStr
    password: str = Field(alias="pass")
    company_id: UUID | None = None


class LoginResponse(BaseModel):
    """Ответ с access-токеном."""

    access_token: str
    token_type: str = "bearer"


class CreateEmployeeRequest(BaseModel):
    """Тело запроса на создание сотрудника администратором."""

    account: EmailStr
    first_name: str
    last_name: str


class CreateEmployeeResponse(BaseModel):
    """Ответ на создание сотрудника."""

    employee_id: UUID
    invite_sent: bool


class RegisterEmployeeRequest(BaseModel):
    """Тело запроса на завершение регистрации сотрудника по инвайту."""

    invite_token: str
    password: str = Field(alias="pass")


class RegisterEmployeeResponse(BaseModel):
    """Ответ на завершение регистрации сотрудника."""

    employee_id: UUID
