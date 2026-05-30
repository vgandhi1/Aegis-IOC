"""Cyber REST routes. All routes require ``cyber:*`` scopes (default-deny)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ...auth.rbac import Principal, require_scopes
from .schemas import (
    CyberAlert,
    RemediationRequest,
    RemediationResult,
    TelemetryAck,
    TelemetrySubmission,
)
from .service import CyberService

router = APIRouter(prefix="/cyber", tags=["cyber"])


def _service(request: Request) -> CyberService:
    return request.app.state.runtime.cyber


@router.post("/telemetry/submit", response_model=TelemetryAck)
async def submit_telemetry(
    body: TelemetrySubmission,
    request: Request,
    _: Principal = Depends(require_scopes("cyber:read")),
) -> TelemetryAck:
    return await _service(request).submit_telemetry(body)


@router.get("/alerts", response_model=list[CyberAlert])
async def list_alerts(
    request: Request,
    limit: int = 200,
    _: Principal = Depends(require_scopes("cyber:read")),
) -> list[CyberAlert]:
    return _service(request).latest(min(max(limit, 1), 1000))


@router.post("/alerts/{alert_id}/remediate", response_model=RemediationResult)
async def remediate(
    alert_id: str,
    body: RemediationRequest,
    request: Request,
    principal: Principal = Depends(require_scopes("cyber:remediate")),
) -> RemediationResult:
    result = await _service(request).remediate(alert_id, body.action, principal.username)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return result
