from fastapi import APIRouter

from app.api.v1.endpoints import struct_adm

api_router = APIRouter(prefix="/org/api/v1")
api_router.include_router(struct_adm.router)
