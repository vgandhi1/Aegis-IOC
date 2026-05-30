"""HealthTech clinical domain schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReconcileRequest(BaseModel):
    patient_id: str = Field(..., examples=["pat_hex_992104"])
    proposed_prescription_code: str = Field(..., examples=["RxNorm:1191"])
    proposed_prescription_display: str = Field(..., examples=["Aspirin"])


class FdaAdverseEventSummary(BaseModel):
    total_matching_case_reports: int
    primary_co_manifestation_consequence: str
    odds_ratio_increase: float


class EvidenceGrounding(BaseModel):
    source_database: str
    api_query_string: str
    peer_reviewed_guideline_citation: str


class ClinicalDecisionSupport(BaseModel):
    contraindication_detected: bool
    severity_index: Literal["NONE", "MODERATE", "CRITICAL"]
    interacting_medication: str | None = None
    fda_adverse_event_summary: FdaAdverseEventSummary | None = None
    evidence_grounding: EvidenceGrounding | None = None


class ProposedAction(BaseModel):
    medication_code: str
    medication_display: str


class ClinicalReport(BaseModel):
    """One clinical grid row."""

    reconciliation_id: str
    patient_id: str
    evaluation_timestamp: str
    proposed_action: ProposedAction
    active_medication_display: str | None = None
    clinical_decision_support: ClinicalDecisionSupport
    human_verified: bool = False
    status: str = "PENDING_REVIEW"


class ReconcileAck(BaseModel):
    reconciliation_id: str
    patient_id: str
    contraindication_flag: bool
    severity_level: str
    alert_message: str
    required_human_actions: list[str]


class OverrideRequest(BaseModel):
    acknowledge_override: bool
    clinician_signature: str = Field(..., min_length=2, examples=["Dr. Lena Park"])


class OverrideResult(BaseModel):
    reconciliation_id: str
    status: str
    signed_by: str
    timestamp: str
