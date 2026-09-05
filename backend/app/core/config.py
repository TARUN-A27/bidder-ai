from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "backend"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "BidGuard AI"
    app_env: str = "development"
    prototype_dataset_root: Path = Path("/home/tarun/TARUN/projects/test-sih-docs")

    azure_document_intelligence_endpoint: str = ""
    azure_document_intelligence_key: SecretStr = SecretStr("")
    azure_document_intelligence_model: str = "prebuilt-layout"

    oracle_user: str = "BIDGUARD_AI"
    oracle_password: str = ""
    oracle_host: str = "localhost"
    oracle_port: int = 1521
    oracle_service: str = "FREEPDB1"
    oracle_pool_min: int = Field(default=1, ge=1)
    oracle_pool_max: int = Field(default=4, ge=1)
    oracle_pool_increment: int = Field(default=1, ge=1)

    storage_root: Path = PROJECT_ROOT / "storage" / "uploads"

    max_upload_files: int = Field(default=100, ge=1, le=1000)
    max_archive_bytes: int = Field(default=100 * 1024 * 1024, ge=1)
    max_pdf_bytes: int = Field(default=25 * 1024 * 1024, ge=1)
    max_total_pdf_bytes: int = Field(default=200 * 1024 * 1024, ge=1)
    max_zip_compression_ratio: float = Field(default=100.0, ge=1.0)

    @property
    def oracle_dsn(self) -> str:
        return (
            f"{self.oracle_host}:{self.oracle_port}/"
            f"{self.oracle_service}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
