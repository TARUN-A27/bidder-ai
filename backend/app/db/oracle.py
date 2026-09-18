from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

import oracledb

from app.core.config import Settings
from app.core.errors import DatabaseUnavailableError


logger = logging.getLogger("bidguard.database")

_pool: oracledb.ConnectionPool | None = None


def initialize_pool(settings: Settings) -> None:
    global _pool

    if _pool is not None:
        return

    if not settings.oracle_password:
        logger.warning(
            "DATABASE POOL SKIPPED | reason=password_unset"
        )
        return

    logger.info(
        "DATABASE POOL START | host=%s port=%s service=%s min=%s max=%s",
        settings.oracle_host, settings.oracle_port, settings.oracle_service,
        settings.oracle_pool_min, settings.oracle_pool_max,
    )
    try:
        _pool = oracledb.create_pool(
            user=settings.oracle_user,
            password=settings.oracle_password,
            dsn=settings.oracle_dsn,
            min=settings.oracle_pool_min,
            max=settings.oracle_pool_max,
            increment=settings.oracle_pool_increment,
        )
    except Exception as exc:
        logger.error("DATABASE POOL FAILED | error_type=%s", type(exc).__name__)
        raise
    logger.info("DATABASE POOL COMPLETE | state=ready")


def close_pool() -> None:
    global _pool

    if _pool is None:
        return

    _pool.close()
    _pool = None
    logger.info("DATABASE POOL STOP | state=closed")


@contextmanager
def acquire_connection() -> Iterator[oracledb.Connection]:
    if _pool is None:
        raise DatabaseUnavailableError("Database connection is unavailable")

    try:
        connection = _pool.acquire()
    except Exception as exc:
        logger.error("DATABASE CONNECTION FAILED | error_type=%s", type(exc).__name__)
        raise
    try:
        yield connection
    finally:
        connection.close()


def database_is_healthy() -> bool:
    try:
        with acquire_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM dual")
                row = cursor.fetchone()
                return bool(row and row[0] == 1)
    except Exception as exc:
        logger.error("DATABASE HEALTH FAILED | error_type=%s", type(exc).__name__)
        return False
