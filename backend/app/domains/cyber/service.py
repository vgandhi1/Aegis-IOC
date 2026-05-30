"""Cyber service: orchestrates ingestion -> inference -> store -> broadcast."""

from __future__ import annotations

from ...core.events import Broadcaster
from ...core.ids import new_id, utc_now_iso
from ...core.store import RingStore
from . import inference
from .schemas import (
    CyberAlert,
    RemediationResult,
    TelemetryAck,
    TelemetrySubmission,
)


class CyberService:
    def __init__(self, store: RingStore, broadcaster: Broadcaster) -> None:
        self._store = store
        self._broadcaster = broadcaster

    async def submit_telemetry(self, payload: TelemetrySubmission) -> TelemetryAck:
        ml_inference, remediation, severity = inference.score(payload)
        triage = inference.triage(payload, ml_inference)
        event_id = new_id("evt")
        alert = CyberAlert(
            alert_id=new_id("alt"),
            associated_event_id=event_id,
            timestamp=utc_now_iso(),
            target_identifier=payload.destination_ip,
            source_ip=payload.source_ip,
            destination_ip=payload.destination_ip,
            destination_port=payload.destination_port,
            severity=severity,
            ml_inference=ml_inference,
            autonomous_remediation=remediation,
            triage=triage,
        )
        self._store.add(alert.alert_id, alert.model_dump())
        await self._broadcaster.publish("cyber", alert.model_dump())

        anomaly_detected = ml_inference.anomaly_score >= 0.85
        return TelemetryAck(
            event_id=event_id,
            tier_1_anomaly_detected=anomaly_detected,
            anomaly_score=ml_inference.anomaly_score,
            remediation_action_initiated=remediation.recommended_action,
            alert_id=alert.alert_id,
        )

    def latest(self, limit: int = 200) -> list[dict]:
        return self._store.latest(limit)

    async def remediate(self, alert_id: str, action: str, acted_by: str) -> RemediationResult | None:
        record = self._store.patch(
            alert_id,
            {"status": f"REMEDIATED:{action}"},
        )
        if record is None:
            return None
        record["autonomous_remediation"]["policy_override_triggered"] = True
        result = RemediationResult(
            alert_id=alert_id,
            action=action,
            status="APPLIED",
            acted_by=acted_by,
            timestamp=utc_now_iso(),
        )
        await self._broadcaster.publish("cyber", {**record, "_event": "remediation"})
        return result
