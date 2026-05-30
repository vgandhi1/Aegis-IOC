"""JWT issuance and verification.

Tokens are signed HS256 JWTs carrying the subject, role, and the expanded scope
list. The gateway and per-route guards verify the signature, issuer, audience,
and expiry before any protected work runs.
"""

from __future__ import annotations

import hmac
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from ..config import get_settings

_ISSUER = "aegis-idp"
_AUDIENCE = "aegis-api"


def verify_password(plain: str, expected: str) -> bool:
    """Constant-time comparison. (Demo store keeps plaintext; real IdP hashes.)"""
    return hmac.compare_digest(plain.encode(), expected.encode())


def create_access_token(*, subject: str, role: str, scopes: list[str], full_name: str) -> tuple[str, int]:
    settings = get_settings()
    expires_delta = timedelta(minutes=settings.access_token_ttl_minutes)
    expire = datetime.now(timezone.utc) + expires_delta
    payload: dict[str, Any] = {
        "sub": subject,
        "name": full_name,
        "role": role,
        "scope": " ".join(scopes),
        "iss": _ISSUER,
        "aud": _AUDIENCE,
        "iat": datetime.now(timezone.utc),
        "exp": expire,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode + validate a token. Raises ``jwt.PyJWTError`` on any failure."""
    settings = get_settings()
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
        audience=_AUDIENCE,
        issuer=_ISSUER,
    )
