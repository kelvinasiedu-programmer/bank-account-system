"""Typed, env-driven configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment or `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API
    api_title: str = "Bank Account System API"
    api_version: str = "1.0.0"
    api_description: str = (
        "Production-grade OOP banking system with tiered-interest savings "
        "and overdraft-enabled checking accounts."
    )

    # Persistence
    storage_path: str = "data/accounts.json"

    # Banking rules — tiered interest
    tier_1_limit: float = 1000.0
    tier_1_rate: float = 0.03
    tier_2_limit: float = 5000.0
    tier_2_rate: float = 0.05
    tier_3_rate: float = 0.07

    # Checking account
    overdraft_limit: float = -500.0
    overdraft_fee: float = 25.0

    # Rate limiting
    rate_limit_requests: int = 30
    rate_limit_window_seconds: int = 60

    # CORS
    cors_origins: list[str] = ["*"]


settings = Settings()
