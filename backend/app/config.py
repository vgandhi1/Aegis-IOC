"""Application configuration.

Values are read from the environment (prefix ``AEGIS_``) with local-dev defaults.

Security note: there is no shipped ``secret_key``. When ``environment`` is
``local`` and no key is supplied, a random one is generated per process — tokens
therefore do not survive a restart, which is correct for a demo. Every other
environment fails to start without ``AEGIS_SECRET_KEY``. The demo users in
``auth.users`` must still be replaced by a real Identity Provider.
"""

from __future__ import annotations

import secrets
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Minimum length for the HS256 signing key. Shorter keys weaken the HMAC.
MIN_SECRET_KEY_LENGTH = 32

# Keys that were published in this repository's history and are therefore public.
# Refused outright so a stale .env cannot silently resurrect one.
_COMPROMISED_SECRET_KEYS = frozenset({"local-dev-only-change-me-please-32+chars"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AEGIS_", env_file=".env", extra="ignore")

    app_name: str = "Aegis IOC"
    environment: str = "local"

    # --- Auth ---
    # No default. Supplied via AEGIS_SECRET_KEY, or generated per process when
    # environment == "local". See _resolve_secret_key below.
    secret_key: str = ""
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

    @model_validator(mode="after")
    def _resolve_secret_key(self) -> "Settings":
        """Fail closed on a missing, short, or publicly-known signing key.

        A forgeable key is a total auth bypass here: ``create_access_token``
        carries ``role`` and ``scope`` in the payload, so anyone able to sign a
        token can grant themselves any scope. The only case that does not raise
        is a local environment with no key configured, which gets an ephemeral
        random key so the demo still starts with no setup.
        """
        key = self.secret_key.strip()

        if key in _COMPROMISED_SECRET_KEYS:
            raise ValueError(
                "AEGIS_SECRET_KEY is set to a value published in this repository's "
                "git history and must be considered public. Generate a new one: "
                "python -c 'import secrets; print(secrets.token_urlsafe(48))'"
            )

        if not key:
            if self.environment != "local":
                raise ValueError(
                    f"AEGIS_SECRET_KEY is required when AEGIS_ENVIRONMENT is "
                    f"'{self.environment}'. Generate one: "
                    "python -c 'import secrets; print(secrets.token_urlsafe(48))'"
                )
            # Local demo: ephemeral per-process key. Tokens are invalidated by a
            # restart, and multi-worker uvicorn would sign with mismatched keys —
            # set AEGIS_SECRET_KEY explicitly if either matters.
            self.secret_key = secrets.token_urlsafe(48)
            return self

        if len(key) < MIN_SECRET_KEY_LENGTH:
            raise ValueError(
                f"AEGIS_SECRET_KEY must be at least {MIN_SECRET_KEY_LENGTH} "
                f"characters (got {len(key)})."
            )

        self.secret_key = key
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
