from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

import oracledb

from app.core.config import Settings
from app.core.errors import DatabaseUnavailableError


logger = logging.getLogger(__name__)

_pool: oracledb.ConnectionPool | None = None


def initialize_pool(settings: Settings) -> None:
    global _pool

    if _pool is not None:
        return

    if not settings.oracle_password:
        logger.warning(
            "Oracle pool not started because ORACLE_PASSWORD is unset"
        )
        return

    logger.info("Starting Oracle connection pool")
    _pool = oracledb.create_pool(
        user=settings.oracle_user,
        password=settings.oracle_password,
        dsn=settings.oracle_dsn,
        min=settings.oracle_pool_min,
        max=settings.oracle_pool_max,
        increment=settings.oracle_pool_increment,
    )
    logger.info("Oracle connection pool started")


def close_pool() -> None:
    global _pool

    if _pool is None:
        return

    _pool.close()
    _pool = None
    logger.info("Oracle connection pool closed")


@contextmanager
def acquire_connection() -> Iterator[oracledb.Connection]:
    if _pool is None:
        raise DatabaseUnavailableError("Database connection is unavailable")

    connection = _pool.acquire()
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
    except Exception:
        logger.exception("Oracle database health check failed")
        return False
