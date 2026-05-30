"""Live market connectors for Aegis Ledger.

* CoinGecko    — high-velocity digital-asset prices (no key) to drive a realistic
  transaction stream and stress the WebSocket batching.
* Alpha Vantage — FX reference rates (query key); cached aggressively because the
  free tier is only 25 requests/day.

All asset ids / currency codes are from controlled constant sets, never raw user
input.
"""

from __future__ import annotations

from typing import Any

from ...config import get_settings
from ...core.http import cached_get_json


async def coingecko_prices(asset_ids: list[str], vs_currency: str = "usd") -> dict[str, float] | None:
    """Return {asset_id: price} for the requested assets (cached briefly)."""
    settings = get_settings()
    ids = ",".join(asset_ids)
    data = await cached_get_json(
        f"coingecko:{ids}:{vs_currency}",
        f"{settings.coingecko_base_url}/simple/price",
        ttl_seconds=4,
        params={"ids": ids, "vs_currencies": vs_currency, "include_24hr_change": "true"},
        headers={"Accept": "application/json"},
    )
    if not data:
        return None
    out: dict[str, float] = {}
    for asset, payload in data.items():
        price = payload.get(vs_currency)
        if isinstance(price, (int, float)):
            out[asset] = float(price)
    return out or None


async def coingecko_market(asset_ids: list[str], vs_currency: str = "usd") -> dict[str, dict[str, Any]] | None:
    """Return price + 24h change keyed by asset (cached briefly)."""
    settings = get_settings()
    ids = ",".join(asset_ids)
    data = await cached_get_json(
        f"coingecko:mkt:{ids}:{vs_currency}",
        f"{settings.coingecko_base_url}/simple/price",
        ttl_seconds=4,
        params={"ids": ids, "vs_currencies": vs_currency, "include_24hr_change": "true"},
        headers={"Accept": "application/json"},
    )
    if not data:
        return None
    out: dict[str, dict[str, Any]] = {}
    for asset, payload in data.items():
        price = payload.get(vs_currency)
        change = payload.get(f"{vs_currency}_24h_change")
        if isinstance(price, (int, float)):
            out[asset] = {"price": float(price), "change_24h": float(change) if change is not None else 0.0}
    return out or None


async def alphavantage_fx(from_currency: str, to_currency: str = "USD") -> float | None:
    """Return the exchange rate from->to (cached 1h due to 25/day free tier)."""
    settings = get_settings()
    if not settings.alphavantage_api_key:
        return None
    data = await cached_get_json(
        f"av:fx:{from_currency}:{to_currency}",
        f"{settings.alphavantage_base_url}/query",
        ttl_seconds=3600,
        params={
            "function": "CURRENCY_EXCHANGE_RATE",
            "from_currency": from_currency,
            "to_currency": to_currency,
            "apikey": settings.alphavantage_api_key,
        },
    )
    if not data:
        return None
    try:
        rate = data["Realtime Currency Exchange Rate"]["5. Exchange Rate"]
        return float(rate)
    except (KeyError, TypeError, ValueError):
        return None
