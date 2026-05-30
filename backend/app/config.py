"""Application configuration.

Values are read from the environment (prefix ``AEGIS_``) with local-dev defaults.

Security note: the default ``secret_key`` is for LOCAL DEVELOPMENT ONLY. It must
be overridden via the environment before any non-local deployment, and the demo
users in ``auth.users`` must be replaced by a real Identity Provider.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AEGIS_", env_file=".env", extra="ignore")

    app_name: str = "Aegis IOC"
    environment: str = "local"

    # --- Auth ---
    # Local-dev default only. Override AEGIS_SECRET_KEY in any real environment.
    secret_key: str = "local-dev-only-change-me-please-32+chars"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 8 * 60

    # --- CORS / frontend ---
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # --- Domain simulators ---
    enable_simulators: bool = True
    cyber_flush_ms: int = 250
    fintech_flush_ms: int = 50
    health_heartbeat_ms: int = 500

    # ring-buffer capacity per domain store
    store_capacity: int = 5000


@lru_cache
def get_settings() -> Settings:
    return Settings()
