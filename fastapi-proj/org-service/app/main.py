from fastapi import FastAPI

from app.api.idempotency import IdempotencyMiddleware
from app.api.v1.router import api_router
from app.core.error_handlers import register_exception_handlers
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(title="org-service")

app.add_middleware(IdempotencyMiddleware)
register_exception_handlers(app)
app.include_router(api_router)
