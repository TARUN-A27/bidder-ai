from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.api.v1 import api_router
from app.core.config import get_settings
from app.db.oracle import close_pool, database_is_healthy, initialize_pool


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    logger.info("Starting %s", settings.app_name)
    initialize_pool(settings)
    try:
        yield
    finally:
        close_pool()
        logger.info("Stopped %s", settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    @application.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    @application.get("/health/database", tags=["health"])
    async def database_health() -> dict[str, str]:
        healthy = await run_in_threadpool(database_is_healthy)
        if not healthy:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "DATABASE_UNAVAILABLE",
                    "message": "Database service is unavailable",
                },
            )
        return {"status": "ok", "database": "connected"}

    application.include_router(api_router, prefix="/api/v1")
    return application


app = create_app()
