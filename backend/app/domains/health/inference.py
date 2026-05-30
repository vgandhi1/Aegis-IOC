"""Mock clinical decision support pipeline.

Tier-1 (BioBERT NER) is represented by direct RxNorm display matching; Tier-2
(Med-PaLM grounded RAG) is represented by lookups against the seeded openFDA-like
knowledge base. Swap for real model + openFDA calls behind the same interface.
"""

from __future__ import annotations

from urllib.parse import quote

from . import knowledge
from .schemas import (
    ClinicalDecisionSupport,
    EvidenceGrounding,
    FdaAdverseEventSummary,
)

_OPENFDA_BASE = "https://api.fda.gov/drug/event.json"


def _fda_query(drug_a: str, drug_b: str) -> str:
    # Build a documented, read-only openFDA query string for grounding display.
    # The drug names are sourced from our controlled RxNorm display set, not raw
    # free-text user input, and are URL-encoded before use.
    search = (
        f"patient.drug.medicinalproduct:{quote(drug_a.upper())}"
        f"+AND+patient.drug.medicinalproduct:{quote(drug_b.upper())}"
    )
    return f"{_OPENFDA_BASE}?search={search}&limit=1"


def evaluate(proposed_display: str, active_medications: list[dict]) -> ClinicalDecisionSupport:
    """Check the proposed drug against every active medication for the patient."""
    for med in active_medications:
        active_display = med["display"]
        interaction = knowledge.lookup_interaction(proposed_display, active_display)
        if interaction is None:
            continue
        return ClinicalDecisionSupport(
            contraindication_detected=True,
            severity_index=interaction["severity"],
            interacting_medication=active_display,
            fda_adverse_event_summary=FdaAdverseEventSummary(
                total_matching_case_reports=interaction["total_reports"],
                primary_co_manifestation_consequence=interaction["consequence"],
                odds_ratio_increase=interaction["odds_ratio"],
            ),
            evidence_grounding=EvidenceGrounding(
                source_database="openFDA Drug Event Repository",
                api_query_string=_fda_query(proposed_display, active_display),
                peer_reviewed_guideline_citation=interaction["citation"],
            ),
        )
    return ClinicalDecisionSupport(contraindication_detected=False, severity_index="NONE")
