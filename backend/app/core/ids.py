"""Identifier and timestamp helpers shared across domains."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone


def utc_now_iso() -> str:
    """RFC3339 / ISO-8601 timestamp in UTC with millisecond precision."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def new_id(prefix: str, nbytes: int = 8) -> str:
    """Generate a short, prefixed, URL-safe hex id (e.g. ``evt_8f3d1a9e4b7c2d10``)."""
    return f"{prefix}_{secrets.token_hex(nbytes)}"
