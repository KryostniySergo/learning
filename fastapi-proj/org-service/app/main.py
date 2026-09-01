from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(title="org-service")

app.include_router(api_router)
