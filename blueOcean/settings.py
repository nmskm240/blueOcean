from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    sqlite_path: Path = Field(
        default=Path("data/blueocean.db"),
        validation_alias="BLUEOCEAN_SQLITE_PATH",
    )
    mt5_secret_key: SecretStr = Field(
        validation_alias="BLUEOCEAN_SECRET_KEY",
    )
    mt5_startup_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        validation_alias="BLUEOCEAN_MT5_STARTUP_TIMEOUT_SECONDS",
    )

@lru_cache
def get_settings() -> Settings:
    """Read and validate settings once per process."""
    return Settings()
