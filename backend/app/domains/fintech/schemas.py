"""FinTech transaction & compliance domain schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ActionProtocol = Literal[
    "CLEARED",
    "MONITOR_FLOW",
    "HOLD_FOR_COMPLIANCE_REVIEW",
    "BLOCK_TRANSACTION",
]


class TransactionEvaluation(BaseModel):
    originating_account: str = Field(..., examples=["acc_intl_88201492"])
    originating_routing_bic: str = Field(..., examples=["CHASUS33XXX"])
    destination_account: str = Field(..., examples=["acc_shell_77411209"])
    destination_routing_bic: str | None = Field(default=None, examples=["BPCKCY22XXX"])
    beneficiary_jurisdiction_country: str = Field(..., min_length=2, max_length=2, examples=["KY"])
    amount: float = Field(..., gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    distinct_beneficiaries_count_1h: int | None = Field(default=None, ge=0)
    historical_max_single_tx_ratio: float | None = Field(default=None, ge=0)


class SanctionHit(BaseModel):
    list_name: str
    matched_term: str
    confidence_match_score: float


class ComplianceDecision(BaseModel):
    risk_score: float
    action_protocol: ActionProtocol
    regulatory_triggers: list[str]


class MlFraudIndicators(BaseModel):
    structured_smurfing_probability: float
    layered_routing_score: float
    anomaly_model_version: str


class NlpComplianceGrounding(BaseModel):
    entity_match_detected: bool
    sanction_list_hits: list[SanctionHit]
    contextual_summary: str


class FinAssessment(BaseModel):
    """One FinTech grid row."""

    assessment_id: str
    associated_transaction_id: str
    timestamp: str
    originating_account: str
    destination_account: str
    beneficiary_jurisdiction_country: str
    amount: float
    currency: str
    compliance_decision: ComplianceDecision
    ml_fraud_indicators: MlFraudIndicators
    nlp_compliance_grounding: NlpComplianceGrounding
    status: str = "OPEN"


class EvaluateAck(BaseModel):
    assessment_id: str
    associated_transaction_id: str
    compliance_decision: ComplianceDecision
    sanction_hit_detected: bool
    flagged_entity_alias: str | None = None


class LedgerActionRequest(BaseModel):
    action: Literal["RELEASE_HOLD", "FREEZE_ASSETS", "FILE_SAR"]


class LedgerActionResult(BaseModel):
    assessment_id: str
    action: str
    status: str
    acted_by: str
    timestamp: str
