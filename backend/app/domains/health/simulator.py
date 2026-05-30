"""Background clinical reconciliation simulator (stand-in for the HL7 router)."""

from __future__ import annotations

import asyncio
import random

from . import knowledge
from .schemas import ReconcileRequest
from .service import HealthService

# proposed prescriptions; some will collide with patients' active meds
_PROPOSALS = [
    ("RxNorm:1191", "Aspirin"),
    ("RxNorm:5640", "Ibuprofen"),
    ("RxNorm:10689", "Tramadol"),
    ("RxNorm:9997", "Spironolactone"),
    ("RxNorm:2670", "Iodinated Contrast"),
    ("RxNorm:161", "Acetaminophen"),
    ("RxNorm:7052", "Amoxicillin"),
]


async def run(service: HealthService, *, interval: float = 3.5) -> None:
    patient_ids = list(knowledge.PATIENTS.keys())
    while True:
        await asyncio.sleep(interval * random.uniform(0.6, 1.4))
        patient_id = random.choice(patient_ids)
        code, display = random.choice(_PROPOSALS)
        await service.reconcile(
            ReconcileRequest(
                patient_id=patient_id,
                proposed_prescription_code=code,
                proposed_prescription_display=display,
            )
        )
