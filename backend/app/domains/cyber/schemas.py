"""Cybersecurity domain schemas (Pydantic v2)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TelemetrySubmission(BaseModel):
    """Minimal ingress payload accepted by the telemetry endpoint."""

    source_ip: str = Field(..., examples=["185.220.101.5"])
    destination_ip: str = Field(..., examples=["10.0.4.112"])
    source_port: int | None = Field(default=None, ge=0, le=65535)
    destination_port: int = Field(..., ge=0, le=65535)
    protocol: Literal["TCP", "UDP", "ICMP"] = "TCP"
    bytes_transferred: int = Field(..., ge=0)
    tcp_flags: list[str] = Field(default_factory=list)
    # optional pre-computed features (else derived heuristically)
    failed_auth_attempts_1m: int | None = Field(default=None, ge=0)
    abuse_confidence_score: int | None = Field(default=None, ge=0, le=100)


class MitreMapping(BaseModel):
    tactic: str
    technique: str
    sub_technique: str


class ConfidenceInterval(BaseModel):
    lower_bound: float
    upper_bound: float


class MLInference(BaseModel):
    anomaly_score: float
    classification: str
    model_version: str
    confidence_intervals: ConfidenceInterval
    mitre_attack_mapping: MitreMapping


class AutonomousRemediation(BaseModel):
    recommended_action: str
    policy_override_triggered: bool = False
    sla_duration_seconds: int
    playbook_id: str


class CyberAlert(BaseModel):
    """Core analytical outbound event (one grid row)."""

    alert_id: str
    associated_event_id: str
    timestamp: str
    target_identifier: str
    source_ip: str
    destination_ip: str
    destination_port: int
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    ml_inference: MLInference
    autonomous_remediation: AutonomousRemediation
    triage: str | None = None
    status: str = "OPEN"


class TelemetryAck(BaseModel):
    status: str = "PROCESSED"
    event_id: str
    tier_1_anomaly_detected: bool
    anomaly_score: float
    websocket_broadcast_queued: bool = True
    remediation_action_initiated: str
    alert_id: str


class RemediationRequest(BaseModel):
    action: Literal["ISOLATE_HOST", "BLOCK_IP", "INVALIDATE_SESSIONS"]


class RemediationResult(BaseModel):
    alert_id: str
    action: str
    status: str
    acted_by: str
    timestamp: str
