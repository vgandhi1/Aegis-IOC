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

    # --- Live external data feeds -------------------------------------------
    # When a feed is enabled and reachable, real data augments/replaces the
    # simulator output. Every connector falls back to the seeded mock on any
    # error, missing key, or timeout, so the system always keeps running.
    http_timeout_seconds: float = 6.0

    # Cyber: AbuseIPDB (header key) + Shodan (query key). Both need keys.
    abuseipdb_api_key: str = ""
    shodan_api_key: str = ""
    abuseipdb_base_url: str = "https://api.abuseipdb.com/api/v2"
    shodan_base_url: str = "https://api.shodan.io"
    # Drives the live AbuseIPDB ingestion poller (kept under the 1,000/day free tier).
    enable_live_cyber: bool = False
    cyber_live_poll_seconds: float = 95.0

    # Health: openFDA + HAPI FHIR (no key required).
    openfda_base_url: str = "https://api.fda.gov"
    openfda_api_key: str = ""  # optional, lifts rate limits
    fhir_base_url: str = "https://hapi.fhir.org/baseR4"
    enable_live_health: bool = True

    # FinTech: CoinGecko (no key) + Alpha Vantage (query key).
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"
    alphavantage_base_url: str = "https://www.alphavantage.co"
    alphavantage_api_key: str = ""
    enable_live_fintech: bool = True
    fintech_live_poll_seconds: float = 6.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
