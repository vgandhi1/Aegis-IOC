"""Live clinical connectors for Aegis Clinical.

* openFDA  — real adverse-event case counts for a drug pair (no key required;
  an optional key lifts rate limits).
* HAPI FHIR — real FHIR R4 Patient / Observation resources from the public
  sandbox (no auth).

Drug names are sourced from the controlled RxNorm display set, not raw user
free-text, and are URL-encoded by httpx before the request is sent.
"""

from __future__ import annotations

from typing import Any

from ...config import get_settings
from ...core.http import cached_get_json


async def openfda_pair_count(drug_a: str, drug_b: str) -> int | None:
    """Total openFDA adverse-event reports co-mentioning both drugs (cached 6h)."""
    settings = get_settings()
    search = (
        f'patient.drug.medicinalproduct:"{drug_a.upper()}"'
        f' AND patient.drug.medicinalproduct:"{drug_b.upper()}"'
    )
    params: dict[str, Any] = {"search": search, "limit": 1}
    if settings.openfda_api_key:
        params["api_key"] = settings.openfda_api_key
    data = await cached_get_json(
        f"openfda:{drug_a.upper()}|{drug_b.upper()}",
        f"{settings.openfda_base_url}/drug/event.json",
        ttl_seconds=6 * 3600,
        params=params,
    )
    if not data:
        return None
    # openFDA returns 404 (-> None here) when there are zero matches.
    try:
        return int(data["meta"]["results"]["total"])
    except (KeyError, TypeError, ValueError):
        return None


def _coding_display(resource: dict[str, Any]) -> str | None:
    try:
        return resource["code"]["coding"][0].get("display")
    except (KeyError, IndexError, TypeError):
        return None


async def fhir_list_patients(limit: int = 10) -> list[dict[str, Any]] | None:
    """Fetch recent FHIR Patient resources from the public sandbox (cached 10m)."""
    settings = get_settings()
    data = await cached_get_json(
        f"fhir:patients:{limit}",
        f"{settings.fhir_base_url}/Patient",
        ttl_seconds=600,
        params={"_count": limit, "_sort": "-_lastUpdated"},
        headers={"Accept": "application/fhir+json"},
    )
    if not data or "entry" not in data:
        return None
    patients: list[dict[str, Any]] = []
    for entry in data.get("entry", []):
        res = entry.get("resource", {})
        if res.get("resourceType") != "Patient":
            continue
        name = ""
        if res.get("name"):
            n = res["name"][0]
            given = " ".join(n.get("given", []))
            name = f"{given} {n.get('family', '')}".strip()
        patients.append(
            {
                "patient_id": f"fhir_{res.get('id')}",
                "fhir_id": res.get("id"),
                "name": name or "(unnamed)",
                "gender": res.get("gender"),
                "birthDate": res.get("birthDate"),
            }
        )
    return patients or None


async def fhir_latest_observation(fhir_patient_id: str, loinc_code: str = "8867-4") -> dict[str, Any] | None:
    """Fetch the latest Observation (default LOINC 8867-4 = heart rate)."""
    settings = get_settings()
    data = await cached_get_json(
        f"fhir:obs:{fhir_patient_id}:{loinc_code}",
        f"{settings.fhir_base_url}/Observation",
        ttl_seconds=300,
        params={"patient": fhir_patient_id, "code": loinc_code, "_count": 1, "_sort": "-date"},
        headers={"Accept": "application/fhir+json"},
    )
    if not data or "entry" not in data:
        return None
    for entry in data.get("entry", []):
        res = entry.get("resource", {})
        if res.get("resourceType") != "Observation":
            continue
        vq = res.get("valueQuantity", {})
        return {
            "display": _coding_display(res),
            "value": vq.get("value"),
            "unit": vq.get("unit"),
            "effective": res.get("effectiveDateTime"),
        }
    return None
