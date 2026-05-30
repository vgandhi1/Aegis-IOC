"""Background telemetry simulator (stand-in for the Kafka/Flink ingest stream)."""

from __future__ import annotations

import asyncio
import random

from .schemas import TelemetrySubmission
from .service import CyberService

_SRC_IPS = ["185.220.101.5", "45.155.205.233", "193.169.255.78", "10.0.2.41", "172.16.5.9"]
_DST_IPS = ["10.0.4.112", "10.0.4.55", "10.0.9.20", "10.0.1.8"]
_PORTS = [22, 22, 3389, 445, 23, 443, 8080]


async def run(service: CyberService, *, interval: float = 1.2) -> None:
    while True:
        await asyncio.sleep(interval * random.uniform(0.5, 1.5))
        port = random.choice(_PORTS)
        suspicious = port in (22, 3389, 445, 23)
        payload = TelemetrySubmission(
            source_ip=random.choice(_SRC_IPS),
            destination_ip=random.choice(_DST_IPS),
            source_port=random.randint(1024, 65535),
            destination_port=port,
            protocol="TCP",
            bytes_transferred=random.randint(64, 4096),
            tcp_flags=["SYN"] if suspicious else random.choice([["SYN", "ACK"], ["PSH", "ACK"]]),
            failed_auth_attempts_1m=random.randint(20, 60) if suspicious else random.randint(0, 4),
            abuse_confidence_score=random.randint(80, 99) if suspicious else random.randint(0, 30),
        )
        await service.submit_telemetry(payload)
