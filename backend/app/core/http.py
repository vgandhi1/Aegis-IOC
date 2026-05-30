"""Shared async HTTP helper for outbound calls to external data feeds.

Security posture (see workspace SSRF rules):
* All destinations are built from operator-controlled, hardcoded base URLs in
  ``Settings`` — never from end-user input. Callers pass only a fixed path and
  query/header values derived from validated, controlled data.
* Only HTTPS endpoints are configured.
* API keys are sent only to their specific provider host (the caller chooses the
  base URL); they are never forwarded to arbitrary/redirected hosts
  (``follow_redirects=False``).
* Failures never surface provider internals to API clients — callers translate a
  ``None`` result into a graceful fallback.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from ..config import get_settings

# Simple in-process TTL cache shared across connectors. Keyed by an opaque
# string the caller controls. Stores (expiry_epoch, value).
_cache: dict[str, tuple[float, Any]] = {}
_cache_lock = asyncio.Lock()


async def cached_get_json(
    cache_key: str,
    url: str,
    *,
    ttl_seconds: float,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Any | None:
    """GET JSON with a TTL cache. Returns parsed JSON or ``None`` on any failure.

    ``url`` must be an operator-configured base URL + fixed path (never raw user
    input). Provider errors are swallowed and reported as ``None`` so callers can
    fall back without leaking internal error details to API clients.
    """
    now = time.time()
    async with _cache_lock:
        hit = _cache.get(cache_key)
        if hit and hit[0] > now:
            return hit[1]

    settings = get_settings()
    if not url.startswith("https://"):
        # Defense-in-depth: only allow HTTPS outbound (no file/ftp/gopher/http).
        return None

    try:
        async with httpx.AsyncClient(
            timeout=settings.http_timeout_seconds, follow_redirects=False
        ) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        # Generic failure: do not propagate provider/internal error details.
        return None

    async with _cache_lock:
        _cache[cache_key] = (now + ttl_seconds, data)
    return data
