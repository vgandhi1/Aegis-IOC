"""Seeded clinical knowledge base.

Reference stand-in for the FHIR patient store + openFDA adverse-event repository
+ BioBERT/Med-PaLM grounding. Static, de-identified demo data only.
"""

from __future__ import annotations

# patient_id -> demographics + active medications
PATIENTS: dict[str, dict] = {
    "pat_hex_992104": {
        "gender": "female",
        "birthDate": "1968-04-12",
        "active_medications": [{"code": "RxNorm:11124", "display": "Warfarin"}],
    },
    "pat_hex_337001": {
        "gender": "male",
        "birthDate": "1955-09-30",
        "active_medications": [{"code": "RxNorm:6809", "display": "Metformin"}],
    },
    "pat_hex_551239": {
        "gender": "female",
        "birthDate": "1981-01-22",
        "active_medications": [{"code": "RxNorm:42347", "display": "Sertraline"}],
    },
    "pat_hex_770488": {
        "gender": "male",
        "birthDate": "1949-07-03",
        "active_medications": [{"code": "RxNorm:29046", "display": "Lisinopril"}],
    },
}


def _key(a: str, b: str) -> frozenset[str]:
    return frozenset({a.upper(), b.upper()})


# pairwise contraindications keyed by the two interacting drug displays
CONTRAINDICATIONS: dict[frozenset[str], dict] = {
    _key("Warfarin", "Aspirin"): {
        "severity": "CRITICAL",
        "consequence": "Severe Gastrointestinal Hemorrhage",
        "total_reports": 24012,
        "odds_ratio": 4.21,
        "citation": "ACC/AHA Guidelines on Dual Antiplatelet Therapy, Section 7.2",
    },
    _key("Warfarin", "Ibuprofen"): {
        "severity": "CRITICAL",
        "consequence": "Increased Bleeding Risk (NSAID interaction)",
        "total_reports": 13110,
        "odds_ratio": 3.55,
        "citation": "Chest CHEST Guideline on Antithrombotic Therapy, Sec 4.1",
    },
    _key("Sertraline", "Tramadol"): {
        "severity": "CRITICAL",
        "consequence": "Serotonin Syndrome",
        "total_reports": 8721,
        "odds_ratio": 5.02,
        "citation": "FDA Drug Safety Communication 2016-SSRI-Opioid",
    },
    _key("Lisinopril", "Spironolactone"): {
        "severity": "MODERATE",
        "consequence": "Hyperkalemia",
        "total_reports": 4502,
        "odds_ratio": 2.10,
        "citation": "KDIGO Clinical Practice Guideline, Potassium Management",
    },
    _key("Metformin", "Iodinated Contrast"): {
        "severity": "MODERATE",
        "consequence": "Lactic Acidosis / Acute Kidney Injury",
        "total_reports": 3340,
        "odds_ratio": 1.95,
        "citation": "ACR Manual on Contrast Media, v2023",
    },
}


def lookup_interaction(drug_a: str, drug_b: str) -> dict | None:
    return CONTRAINDICATIONS.get(_key(drug_a, drug_b))
