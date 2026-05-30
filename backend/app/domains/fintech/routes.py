"""FinTech REST routes. Requires ``fintech:*`` scopes (default-deny)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ...auth.rbac import Principal, require_scopes
from .schemas import (
    EvaluateAck,
    FinAssessment,
    LedgerActionRequest,
    LedgerActionResult,
    TransactionEvaluation,
)
from .service import FintechService

router = APIRouter(prefix="/fintech", tags=["fintech"])


def _service(request: Request) -> FintechService:
    return request.app.state.runtime.fintech


@router.post("/transaction/evaluate", response_model=EvaluateAck)
async def evaluate(
    body: TransactionEvaluation,
    request: Request,
    _: Principal = Depends(require_scopes("fintech:read")),
) -> EvaluateAck:
    return await _service(request).evaluate(body)


@router.get("/assessments", response_model=list[FinAssessment])
async def list_assessments(
    request: Request,
    limit: int = 200,
    _: Principal = Depends(require_scopes("fintech:read")),
) -> list[FinAssessment]:
    return _service(request).latest(min(max(limit, 1), 1000))


@router.post("/assessments/{assessment_id}/action", response_model=LedgerActionResult)
async def ledger_action(
    assessment_id: str,
    body: LedgerActionRequest,
    request: Request,
    principal: Principal = Depends(require_scopes("fintech:transact")),
) -> LedgerActionResult:
    result = await _service(request).ledger_action(assessment_id, body.action, principal.username)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return result
