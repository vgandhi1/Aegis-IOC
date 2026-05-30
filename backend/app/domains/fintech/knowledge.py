"""Seeded AML/sanctions knowledge base.

Reference stand-in for OFAC/EU/UN sanctions directories and the FinBERT semantic
matcher. Static demo data only.
"""

from __future__ import annotations

# High-risk / monitored jurisdictions (illustrative offshore + FATF watch).
HIGH_RISK_JURISDICTIONS = {"KY", "PA", "VG", "SC", "BS", "VU", "KP", "IR"}

# Account-fragment -> OFAC-style SDN alias. The reference matches on substrings
# of the (non-PII, synthetic) account identifier to simulate fuzzy entity match.
SANCTIONED_ACCOUNT_ALIASES: dict[str, str] = {
    "shell": "Shell Corp Proxy Logistics",
    "77411209": "Shell Corp Proxy Logistics",
    "proxy": "Eastbridge Proxy Holdings",
    "darknet": "Meridian Darknet Exchange",
}

# BIC prefixes flagged as elevated correspondent-bank risk.
ELEVATED_RISK_BICS = {"BPCK", "PRVT", "OFFS"}


def match_sanctions(account: str) -> tuple[str, float] | None:
    lowered = account.lower()
    for fragment, alias in SANCTIONED_ACCOUNT_ALIASES.items():
        if fragment in lowered:
            return alias, 0.975
    return None
