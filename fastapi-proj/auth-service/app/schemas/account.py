from pydantic import BaseModel


class CheckAccountResponse(BaseModel):
    available: bool
