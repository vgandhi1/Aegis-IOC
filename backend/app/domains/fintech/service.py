"""FinTech service: evaluate transactions -> store -> broadcast.

Flagged transactions (risk > 0.70) are broadcast immediately (<50ms target);
cleared/monitored ones use the buffered channel lifecycle.
"""

from __future__ import annotations

from ...core.events import Broadcaster
from ...core.ids import new_id, utc_now_iso
from ...core.store import RingStore
from . import inference
from .schemas import (
    EvaluateAck,
    FinAssessment,
    LedgerActionResult,
    TransactionEvaluation,
)

_FLAG_THRESHOLD = 0.70


class FintechService:
    def __init__(self, store: RingStore, broadcaster: Broadcaster) -> None:
        self._store = store
        self._broadcaster = broadcaster

    async def evaluate(self, body: TransactionEvaluation) -> EvaluateAck:
        decision, indicators, grounding = inference.evaluate(body)
        assessment = FinAssessment(
            assessment_id=new_id("fin_risk"),
            associated_transaction_id=new_id("tx"),
            timestamp=utc_now_iso(),
            originating_account=body.originating_account,
            destination_account=body.destination_account,
            beneficiary_jurisdiction_country=body.beneficiary_jurisdiction_country,
            amount=body.amount,
            currency=body.currency,
            compliance_decision=decision,
            ml_fraud_indicators=indicators,
            nlp_compliance_grounding=grounding,
        )
        self._store.add(assessment.assessment_id, assessment.model_dump())

        immediate = decision.risk_score > _FLAG_THRESHOLD
        await self._broadcaster.publish("fintech", assessment.model_dump(), immediate=immediate)

        flagged_alias = (
            grounding.sanction_list_hits[0].matched_term if grounding.sanction_list_hits else None
        )
        return EvaluateAck(
            assessment_id=assessment.assessment_id,
            associated_transaction_id=assessment.associated_transaction_id,
            compliance_decision=decision,
            sanction_hit_detected=grounding.entity_match_detected,
            flagged_entity_alias=flagged_alias,
        )

    def latest(self, limit: int = 200) -> list[dict]:
        return self._store.latest(limit)

    async def ledger_action(self, assessment_id: str, action: str, acted_by: str) -> LedgerActionResult | None:
        status_map = {
            "RELEASE_HOLD": "RELEASED",
            "FREEZE_ASSETS": "ASSETS_FROZEN",
            "FILE_SAR": "SAR_FILED",
        }
        record = self._store.patch(assessment_id, {"status": status_map.get(action, action)})
        if record is None:
            return None
        await self._broadcaster.publish("fintech", {**record, "_event": "ledger_action"}, immediate=True)
        return LedgerActionResult(
            assessment_id=assessment_id,
            action=action,
            status=status_map.get(action, action),
            acted_by=acted_by,
            timestamp=utc_now_iso(),
        )
