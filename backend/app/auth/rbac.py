"""Authentication + authorization dependencies.

* ``get_current_principal`` — authenticate the bearer token (default-deny).
* ``require_scopes(...)`` — authorize a specific action; returns a dependency
  that enforces the caller holds every required scope.

Errors are intentionally generic to clients (no account-existence leakage); the
detailed reason stays server-side.
"""

from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .security import decode_access_token

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    username: str
    full_name: str
    role: str
    scopes: frozenset[str]

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes


async def get_current_principal(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Principal:
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(creds.credentials)
    except jwt.PyJWTError:
        # Generic message: do not reveal whether token is expired/malformed/etc.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    scopes = frozenset((payload.get("scope") or "").split())
    return Principal(
        username=payload.get("sub", ""),
        full_name=payload.get("name", ""),
        role=payload.get("role", ""),
        scopes=scopes,
    )


def require_scopes(*required: str):
    """Build a dependency that enforces all ``required`` scopes are present."""

    async def _guard(principal: Principal = Depends(get_current_principal)) -> Principal:
        missing = [scope for scope in required if not principal.has_scope(scope)]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient privileges for this operation",
            )
        return principal

    return _guard
