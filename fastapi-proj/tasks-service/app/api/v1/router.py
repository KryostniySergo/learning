from fastapi import APIRouter

from app.api.v1.endpoints import task

api_router = APIRouter(prefix="/tasks/api/v1")
api_router.include_router(task.router)
