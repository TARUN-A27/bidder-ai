from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path(
    os.getenv("BIDGUARD_DATA_ROOT", str(PROJECT_ROOT / "data"))
).expanduser()


def oracle_connection_kwargs() -> dict[str, str]:
    password = os.getenv("ORACLE_PASSWORD", "")
    if not password:
        raise RuntimeError(
            "ORACLE_PASSWORD must be set before running a seed script"
        )

    host = os.getenv("ORACLE_HOST", "localhost")
    port = os.getenv("ORACLE_PORT", "1521")
    service = os.getenv("ORACLE_SERVICE", "FREEPDB1")
    return {
        "user": os.getenv("ORACLE_USER", "BIDGUARD_AI"),
        "password": password,
        "dsn": os.getenv("ORACLE_DSN", f"{host}:{port}/{service}"),
    }
