"""WebSocket live-stream routes.

Authorization is enforced on the WebSocket handshake: the bearer token is passed
as a ``token`` query parameter, verified, and checked for the domain read scope
before the socket is accepted (default-deny).
"""

from __future__ import annotations

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from ..auth.security import decode_access_token

router = APIRouter()

# domain channel -> scope required to subscribe
_CHANNEL_SCOPES = {
    "cyber": "cyber:read",
    "health": "clinical:read",
    "fintech": "fintech:read",
}


@router.websocket("/ws/{domain}")
async def domain_stream(websocket: WebSocket, domain: str, token: str = Query(default="")) -> None:
    required = _CHANNEL_SCOPES.get(domain)
    if required is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    scopes = set((payload.get("scope") or "").split())
    if required not in scopes:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    broadcaster = websocket.app.state.runtime.broadcaster
    channel = broadcaster.channel(domain)
    await channel.connect(websocket)
    try:
        # send a small snapshot of recent records so the grid hydrates instantly
        store = getattr(websocket.app.state.runtime, f"{domain}_store")
        await websocket.send_json({"channel": domain, "batch": store.latest(100), "snapshot": True})
        while True:
            # keep the connection alive; client is read-only on this socket
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await channel.disconnect(websocket)
