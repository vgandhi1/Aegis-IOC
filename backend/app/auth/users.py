"""Demo identity store and the RBAC role matrix.

LOCAL DEMO ONLY. In production these users come from an Identity Provider (IdP)
and passwords are never stored in source. Passwords here are intentionally
trivial and exist only to exercise the login flow locally.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# OAuth2-style scopes. ``<domain>:*`` is a wildcard expanded at token issuance.
ALL_SCOPES = [
    "cyber:read",
    "cyber:remediate",
    "clinical:read",
    "clinical:write",
    "fintech:read",
    "fintech:transact",
    "admin:manage",
]


@dataclass(frozen=True)
class Role:
    key: str
    label: str
    tabs: list[str]
    scopes: list[str]
    actions: list[str] = field(default_factory=list)


ROLES: dict[str, Role] = {
    "security_analyst": Role(
        key="security_analyst",
        label="Infrastructure Security Analyst",
        tabs=["cyber"],
        scopes=["cyber:read", "cyber:remediate"],
        actions=["Isolate Network Node", "Invalidate Session Tokens", "Block Target IPs"],
    ),
    "clinical_provider": Role(
        key="clinical_provider",
        label="Attending Clinical Provider",
        tabs=["health"],
        scopes=["clinical:read", "clinical:write"],
        actions=["Approve Prescription Overrides", "Sign Medical Chart Records"],
    ),
    "compliance_officer": Role(
        key="compliance_officer",
        label="FinTech Compliance Officer",
        tabs=["fintech"],
        scopes=["fintech:read", "fintech:transact"],
        actions=["Release Ledger Hold", "Freeze Beneficiary Assets", "File Suspicious Activity Report"],
    ),
    "governance_board": Role(
        key="governance_board",
        label="Institutional Governance Board",
        tabs=["cyber", "health", "fintech", "admin"],
        # wildcards expanded to concrete scopes at issuance time
        scopes=["cyber:*", "clinical:*", "fintech:*", "admin:manage"],
        actions=["Modify AI Evaluation Thresholds", "Roll Back Model Versions"],
    ),
}


@dataclass(frozen=True)
class DemoUser:
    username: str
    password: str  # demo only
    full_name: str
    role_key: str


DEMO_USERS: dict[str, DemoUser] = {
    "analyst": DemoUser("analyst", "demo", "Dana Okafor", "security_analyst"),
    "clinician": DemoUser("clinician", "demo", "Dr. Lena Park", "clinical_provider"),
    "officer": DemoUser("officer", "demo", "Marco Reyes", "compliance_officer"),
    "governor": DemoUser("governor", "demo", "Aria Sundqvist", "governance_board"),
}


def expand_scopes(scopes: list[str]) -> list[str]:
    """Expand ``<domain>:*`` wildcards into concrete scopes."""
    expanded: set[str] = set()
    for scope in scopes:
        if scope.endswith(":*"):
            domain = scope.split(":", 1)[0]
            expanded.update(s for s in ALL_SCOPES if s.startswith(f"{domain}:"))
        else:
            expanded.add(scope)
    return sorted(expanded)
