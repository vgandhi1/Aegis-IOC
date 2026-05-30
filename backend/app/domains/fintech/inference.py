"""Mock FinTech ML pipeline.

Tier-1 (Isolation Forest + XGBoost ensemble) -> deterministic numeric outlier
scoring. Tier-2 (FinBERT + Llama-3-Finance) -> sanctions/layering grounding.
Swap behind the same interface for real models + sanctions feeds.
"""

from __future__ import annotations

from . import knowledge
from .schemas import (
    ComplianceDecision,
    MlFraudIndicators,
    NlpComplianceGrounding,
    SanctionHit,
)

ANOMALY_MODEL_VERSION = "fin_isolation_forest_v4.2"

_STRUCTURING_THRESHOLD = 10000.0  # CTR / structuring reference threshold (USD)


def _tier1_score(payload) -> tuple[float, float, float]:
    """Return (risk_score, smurfing_prob, layering_score)."""
    amount = payload.amount
    high_risk_jx = payload.beneficiary_jurisdiction_country.upper() in knowledge.HIGH_RISK_JURISDICTIONS
    bic_prefix = (payload.destination_routing_bic or "")[:4].upper()
    elevated_bic = bic_prefix in knowledge.ELEVATED_RISK_BICS

    # large-amount factor (saturating)
    amount_factor = min(amount / 1_000_000.0, 1.0)
    # structuring: many distinct beneficiaries just under threshold
    distinct = payload.distinct_beneficiaries_count_1h or 0
    near_threshold = 0.0
    if 0 < amount < _STRUCTURING_THRESHOLD and amount >= _STRUCTURING_THRESHOLD * 0.8:
        near_threshold = 0.4
    smurfing = min(0.15 * distinct + near_threshold, 0.99)

    variance = payload.historical_max_single_tx_ratio or 1.0
    layering = min(0.10 * variance + (0.4 if elevated_bic else 0.0), 0.99)

    risk = (
        0.30 * amount_factor
        + 0.25 * smurfing
        + 0.20 * layering
        + (0.35 if high_risk_jx else 0.0)
    )
    risk = min(max(risk, 0.01), 0.999)
    return round(risk, 4), round(smurfing, 4), round(layering, 4)


def _action(risk: float, sanction_hit: bool) -> tuple[str, list[str]]:
    if sanction_hit or risk >= 0.85:
        return "HOLD_FOR_COMPLIANCE_REVIEW", ["BSA_31_CFR_1010", "FATF_Recommendation_16"]
    if risk >= 0.70:
        return "HOLD_FOR_COMPLIANCE_REVIEW", ["BSA_31_CFR_1010"]
    if risk >= 0.40:
        return "MONITOR_FLOW", []
    return "CLEARED", []


def evaluate(payload) -> tuple[ComplianceDecision, MlFraudIndicators, NlpComplianceGrounding]:
    risk, smurfing, layering = _tier1_score(payload)

    sanction_hits: list[SanctionHit] = []
    matched_alias: str | None = None
    # Tier-2 semantic matching: a direct OFAC SDN hit always surfaces; the
    # broader FinBERT layering pass is what is gated behind the >0.70 Tier-1 score.
    match = knowledge.match_sanctions(payload.destination_account)
    if match:
        alias, confidence = match
        matched_alias = alias
        sanction_hits.append(
            SanctionHit(list_name="OFAC_SDN_LIST", matched_term=alias, confidence_match_score=confidence)
        )
        # A confirmed SDN match dominates the numeric Tier-1 score.
        risk = round(max(risk, 0.918), 4)

    protocol, triggers = _action(risk, bool(sanction_hits))

    if sanction_hits:
        summary = (
            f"Transaction flagged due to sudden asset-flight velocity targeting "
            f"{payload.beneficiary_jurisdiction_country}. Entity matches active OFAC SDN "
            f"proxy alias '{matched_alias}'."
        )
    elif protocol in ("HOLD_FOR_COMPLIANCE_REVIEW", "MONITOR_FLOW"):
        summary = (
            f"Elevated risk: {payload.amount:,.2f} {payload.currency} routed to "
            f"{payload.beneficiary_jurisdiction_country}. Layering/structuring indicators present."
        )
    else:
        summary = "No adverse AML indicators detected; cleared for settlement."

    decision = ComplianceDecision(
        risk_score=risk, action_protocol=protocol, regulatory_triggers=triggers
    )
    indicators = MlFraudIndicators(
        structured_smurfing_probability=smurfing,
        layered_routing_score=layering,
        anomaly_model_version=ANOMALY_MODEL_VERSION,
    )
    grounding = NlpComplianceGrounding(
        entity_match_detected=bool(sanction_hits),
        sanction_list_hits=sanction_hits,
        contextual_summary=summary,
    )
    return decision, indicators, grounding
