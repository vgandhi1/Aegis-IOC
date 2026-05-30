"""Live threat-intelligence connectors for Aegis Threat.

* AbuseIPDB — IP abuse confidence scoring (header API key).
* Shodan    — exposed ports / vulnerabilities for blast-radius context.

Both require an API key; without one (or on any error) the caller falls back to
seeded/heuristic data. Source IPs are validated as real IP literals before use
to avoid SSRF via crafted host strings.
"""

from __future__ import annotations

import ipaddress
from typing import Any

from ...config import get_settings
from ...core.http import cached_get_json


def is_public_ip(value: str) -> bool:
    """True only for syntactically valid, globally-routable IP addresses.

    Rejects private/loopback/link-local/reserved ranges so enrichment lookups
    cannot be pointed at internal infrastructure (SSRF hardening).
    """
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast)


async def abuseipdb_check(ip: str) -> dict[str, Any] | None:
    """Return AbuseIPDB confidence data for ``ip`` (cached 1h), or None."""
    settings = get_settings()
    if not settings.abuseipdb_api_key or not is_public_ip(ip):
        return None
    data = await cached_get_json(
        f"abuseipdb:{ip}",
        f"{settings.abuseipdb_base_url}/check",
        ttl_seconds=3600,
        params={"ipAddress": ip, "maxAgeInDays": 90},
        # Key is sent only to the configured AbuseIPDB host.
        headers={"Key": settings.abuseipdb_api_key, "Accept": "application/json"},
    )
    if not data or "data" not in data:
        return None
    d = data["data"]
    return {
        "abuse_confidence_score": d.get("abuseConfidenceScore", 0),
        "total_reports": d.get("totalReports", 0),
        "country_code": d.get("countryCode"),
        "isp": d.get("isp"),
        "domain": d.get("domain"),
        "usage_type": d.get("usageType"),
    }


async def shodan_host(ip: str) -> dict[str, Any] | None:
    """Return Shodan exposure summary for ``ip`` (cached 1h), or None."""
    settings = get_settings()
    if not settings.shodan_api_key or not is_public_ip(ip):
        return None
    data = await cached_get_json(
        f"shodan:{ip}",
        f"{settings.shodan_base_url}/shodan/host/{ip}",
        ttl_seconds=3600,
        params={"key": settings.shodan_api_key},
    )
    if not data:
        return None
    return {
        "open_ports": data.get("ports", []),
        "hostnames": data.get("hostnames", []),
        "organization": data.get("org"),
        "operating_system": data.get("os"),
        "vulnerabilities": list(data.get("vulns", []))[:25],
        "country_code": data.get("country_code"),
    }
