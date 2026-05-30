"""Mock cyber ML pipeline.

Reference stand-in for the production Tier-1 XGBoost classifier and Tier-2
Llama-3 triage agent. Scores are deterministic heuristics over the telemetry so
demos and tests are reproducible. Swap this module for real model runtimes; the
service only depends on ``score`` and ``triage``.
"""

from __future__ import annotations

from .schemas import (
    AutonomousRemediation,
    ConfidenceInterval,
    MitreMapping,
    MLInference,
)

MODEL_VERSION = "xgb_threat_v2.4.1"

# suspicious destination ports -> (classification, mitre, playbook)
_PORT_SIGNATURES = {
    22: ("Brute_Force_SSH_Tunneling", ("TA0001_Initial_Access", "T1110_Brute_Force", "T1110.001_Credential_Stuffing"), "pb_ssh_contain_v1", "ISOLATE_HOST"),
    3389: ("RDP_Credential_Stuffing", ("TA0001_Initial_Access", "T1110_Brute_Force", "T1110.001_Credential_Stuffing"), "pb_rdp_contain_v1", "ISOLATE_HOST"),
    445: ("SMB_Lateral_Movement", ("TA0008_Lateral_Movement", "T1021_Remote_Services", "T1021.002_SMB_Admin_Shares"), "pb_smb_contain_v1", "ISOLATE_HOST"),
    23: ("Telnet_Exploitation", ("TA0001_Initial_Access", "T1133_External_Remote_Services", "T1133_External_Remote_Services"), "pb_telnet_block_v1", "BLOCK_IP"),
}


def _severity(score: float) -> str:
    if score >= 0.85:
        return "CRITICAL"
    if score >= 0.60:
        return "HIGH"
    if score >= 0.35:
        return "MEDIUM"
    return "LOW"


def score(payload) -> tuple[MLInference, AutonomousRemediation, str]:
    """Tier-1 + remediation. Returns (inference, remediation, severity)."""
    sig = _PORT_SIGNATURES.get(payload.destination_port)
    classification = sig[0] if sig else "Network_Anomaly_Generic"
    tactic, technique, sub = (
        sig[1] if sig else ("TA0007_Discovery", "T1046_Network_Service_Scanning", "T1046_Network_Service_Scanning")
    )
    playbook = sig[2] if sig else "pb_generic_review_v1"
    action = sig[3] if sig else "MONITOR"

    base = 0.45 if sig else 0.25
    abuse = (payload.abuse_confidence_score or (96 if sig else 20)) / 100.0
    failed = payload.failed_auth_attempts_1m if payload.failed_auth_attempts_1m is not None else (42 if sig else 3)
    failed_factor = min(failed / 50.0, 1.0)
    syn_only = payload.tcp_flags == ["SYN"]

    raw = base + 0.35 * abuse + 0.18 * failed_factor + (0.06 if syn_only else 0.0)
    anomaly = round(min(max(raw, 0.01), 0.999), 4)

    inference = MLInference(
        anomaly_score=anomaly,
        classification=classification,
        model_version=MODEL_VERSION,
        confidence_intervals=ConfidenceInterval(
            lower_bound=round(max(anomaly - 0.05, 0.0), 3),
            upper_bound=round(min(anomaly + 0.03, 1.0), 3),
        ),
        mitre_attack_mapping=MitreMapping(tactic=tactic, technique=technique, sub_technique=sub),
    )
    remediation = AutonomousRemediation(
        recommended_action=action if anomaly >= 0.85 else "MONITOR",
        policy_override_triggered=False,
        sla_duration_seconds=300 if anomaly >= 0.85 else 1800,
        playbook_id=playbook,
    )
    return inference, remediation, _severity(anomaly)


def triage(payload, inference: MLInference) -> str | None:
    """Tier-2 agentic triage (only when Tier-1 score exceeds 0.85)."""
    if inference.anomaly_score < 0.85:
        return None
    return (
        f"Tier-2 agent: source {payload.source_ip} matches active threat-feed indicators "
        f"({inference.mitre_attack_mapping.technique}). Blast radius limited to a single "
        f"destination host on port {payload.destination_port}. Recommended containment "
        f"within the 300s SLA."
    )
