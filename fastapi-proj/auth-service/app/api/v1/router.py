from fastapi import APIRouter

from app.api.v1.endpoints import auth, employee, profile

api_router = APIRouter(prefix="/auth/api/v1")
api_router.include_router(auth.router)
api_router.include_router(employee.router)
api_router.include_router(profile.router)
