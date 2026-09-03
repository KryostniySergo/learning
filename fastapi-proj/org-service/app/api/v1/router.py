from fastapi import APIRouter

from app.api.v1.endpoints import position, struct_adm

api_router = APIRouter(prefix="/org/api/v1")
api_router.include_router(struct_adm.router)
api_router.include_router(position.router)
