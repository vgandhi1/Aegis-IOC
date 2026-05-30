"""Authentication routes: login (token issuance), identity, and role catalog."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from .rbac import Principal, get_current_principal
from .security import create_access_token, verify_password
from .users import DEMO_USERS, ROLES, expand_scopes

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str
    full_name: str
    scopes: list[str]
    tabs: list[str]


class MeResponse(BaseModel):
    username: str
    full_name: str
    role: str
    scopes: list[str]
    tabs: list[str]
    actions: list[str]


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    user = DEMO_USERS.get(body.username)
    # Generic failure message — do not reveal whether the username exists.
    if user is None or not verify_password(body.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    role = ROLES[user.role_key]
    scopes = expand_scopes(role.scopes)
    token, ttl = create_access_token(
        subject=user.username, role=role.key, scopes=scopes, full_name=user.full_name
    )
    return TokenResponse(
        access_token=token,
        expires_in=ttl,
        role=role.key,
        full_name=user.full_name,
        scopes=scopes,
        tabs=role.tabs,
    )


@router.get("/me", response_model=MeResponse)
async def me(principal: Principal = Depends(get_current_principal)) -> MeResponse:
    role = ROLES.get(principal.role)
    return MeResponse(
        username=principal.username,
        full_name=principal.full_name,
        role=principal.role,
        scopes=sorted(principal.scopes),
        tabs=role.tabs if role else [],
        actions=role.actions if role else [],
    )
