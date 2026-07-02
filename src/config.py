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
        "OOP banking service with tiered-interest savings and overdraft-enabled "
        "checking accounts. Money handled with decimal.Decimal."
    )

    # Persistence
    storage_path: str = "data/accounts.json"
    seed_demo_data: bool = True

    # Banking rules: tiered interest
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

    # CORS. Default to same-origin only; set explicit origins in production.
    # A "*" entry allows any origin but forces credentials off (see main.py).
    cors_origins: list[str] = ["*"]

    # Auth. When set, destructive endpoints require this key in the X-API-Key
    # header. Left unset, those endpoints fail closed (503) so the public demo
    # can never be wiped by an anonymous caller.
    admin_api_key: str | None = None


settings = Settings()
