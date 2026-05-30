"""HealthTech service: reconcile proposed prescriptions against active meds."""

from __future__ import annotations

from ...config import get_settings
from ...core.events import Broadcaster
from ...core.ids import new_id, utc_now_iso
from ...core.store import RingStore
from . import connectors, inference, knowledge
from .schemas import (
    ClinicalReport,
    OverrideResult,
    ProposedAction,
    ReconcileAck,
    ReconcileRequest,
)

_SEVERITY_MESSAGE = {
    "CRITICAL": "{consequence} Risk detected via openFDA historical profile matching.",
    "MODERATE": "{consequence} possible; clinical correlation advised.",
    "NONE": "No contraindication detected against active medications.",
}


class HealthService:
    def __init__(self, store: RingStore, broadcaster: Broadcaster) -> None:
        self._store = store
        self._broadcaster = broadcaster

    async def reconcile(self, body: ReconcileRequest) -> ReconcileAck:
        patient = knowledge.PATIENTS.get(body.patient_id)
        active_meds = patient["active_medications"] if patient else []
        cds = inference.evaluate(body.proposed_prescription_display, active_meds)

        # Live grounding: replace the seeded case count with the real openFDA
        # total when a contraindication is found and the feed is enabled.
        if (
            get_settings().enable_live_health
            and cds.contraindication_detected
            and cds.fda_adverse_event_summary
            and cds.interacting_medication
        ):
            real_total = await connectors.openfda_pair_count(
                body.proposed_prescription_display, cds.interacting_medication
            )
            if real_total is not None:
                cds.fda_adverse_event_summary.total_matching_case_reports = real_total
                if cds.evidence_grounding:
                    cds.evidence_grounding.source_database = "openFDA Drug Event Repository (live)"

        report = ClinicalReport(
            reconciliation_id=new_id("rec"),
            patient_id=body.patient_id,
            evaluation_timestamp=utc_now_iso(),
            proposed_action=ProposedAction(
                medication_code=body.proposed_prescription_code,
                medication_display=body.proposed_prescription_display,
            ),
            active_medication_display=cds.interacting_medication,
            clinical_decision_support=cds,
        )
        self._store.add(report.reconciliation_id, report.model_dump())
        await self._broadcaster.publish("health", report.model_dump())

        consequence = (
            cds.fda_adverse_event_summary.primary_co_manifestation_consequence
            if cds.fda_adverse_event_summary
            else ""
        )
        message = _SEVERITY_MESSAGE[cds.severity_index].format(consequence=consequence).strip()
        actions = (
            ["manual_override_checkbox_acknowledgement", "clinician_electronic_signature_seal"]
            if cds.contraindication_detected
            else []
        )
        return ReconcileAck(
            reconciliation_id=report.reconciliation_id,
            patient_id=body.patient_id,
            contraindication_flag=cds.contraindication_detected,
            severity_level=cds.severity_index,
            alert_message=message,
            required_human_actions=actions,
        )

    def latest(self, limit: int = 200) -> list[dict]:
        return self._store.latest(limit)

    async def import_fhir_patients(self, limit: int = 8) -> dict:
        """Pull real FHIR patients from the public sandbox and register them.

        Registered patients become available for reconciliation. Each imported
        patient is seeded with a Warfarin active medication so the live openFDA
        contraindication path can be demonstrated end-to-end.
        """
        patients = await connectors.fhir_list_patients(limit)
        if not patients:
            return {"imported": 0, "patients": [], "note": "FHIR sandbox unavailable or returned no patients."}
        imported = []
        for p in patients:
            obs = await connectors.fhir_latest_observation(p["fhir_id"])
            knowledge.PATIENTS[p["patient_id"]] = {
                "gender": p.get("gender"),
                "birthDate": p.get("birthDate"),
                # seed a known interacting drug so the demo can surface a conflict
                "active_medications": [{"code": "RxNorm:11124", "display": "Warfarin"}],
            }
            imported.append({**p, "latest_observation": obs})
        return {"imported": len(imported), "patients": imported, "note": None}

    async def override(
        self, reconciliation_id: str, *, acknowledged: bool, signature: str
    ) -> OverrideResult | None:
        if not acknowledged:
            return None
        record = self._store.patch(
            reconciliation_id, {"human_verified": True, "status": "OVERRIDE_SIGNED"}
        )
        if record is None:
            return None
        await self._broadcaster.publish("health", {**record, "_event": "override"})
        return OverrideResult(
            reconciliation_id=reconciliation_id,
            status="OVERRIDE_SIGNED",
            signed_by=signature,
            timestamp=utc_now_iso(),
        )
