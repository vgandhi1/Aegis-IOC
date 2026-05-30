"""HealthTech REST routes. Requires ``clinical:*`` scopes (default-deny).

Note: an audit log of every view/mutation/override is required by HIPAA; the
reference relies on server-side request logging without recording PHI payloads.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ...auth.rbac import Principal, require_scopes
from .schemas import (
    ClinicalReport,
    OverrideRequest,
    OverrideResult,
    ReconcileAck,
    ReconcileRequest,
)
from .service import HealthService

router = APIRouter(prefix="/health", tags=["health"])


def _service(request: Request) -> HealthService:
    return request.app.state.runtime.health


@router.post("/clinical/reconcile", response_model=ReconcileAck)
async def reconcile(
    body: ReconcileRequest,
    request: Request,
    _: Principal = Depends(require_scopes("clinical:read")),
) -> ReconcileAck:
    return await _service(request).reconcile(body)


@router.get("/clinical/reports", response_model=list[ClinicalReport])
async def list_reports(
    request: Request,
    limit: int = 200,
    _: Principal = Depends(require_scopes("clinical:read")),
) -> list[ClinicalReport]:
    return _service(request).latest(min(max(limit, 1), 1000))


@router.post("/clinical/reports/{reconciliation_id}/override", response_model=OverrideResult)
async def override(
    reconciliation_id: str,
    body: OverrideRequest,
    request: Request,
    principal: Principal = Depends(require_scopes("clinical:write")),
) -> OverrideResult:
    result = await _service(request).override(
        reconciliation_id, acknowledged=body.acknowledge_override, signature=body.clinician_signature
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Override requires acknowledgement and a valid report id",
        )
    return result
