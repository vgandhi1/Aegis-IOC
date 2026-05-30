"""Background transaction simulator (stand-in for the RabbitMQ event bus)."""

from __future__ import annotations

import asyncio
import random

from .schemas import TransactionEvaluation
from .service import FintechService

_ORIG_ACCOUNTS = ["acc_intl_88201492", "acc_corp_55012", "acc_retail_99210"]
_ORIG_BICS = ["CHASUS33XXX", "BARCGB22XXX", "DEUTDEFFXXX"]
_DEST_NORMAL = ["acc_vendor_44110", "acc_payroll_22013", "acc_supplier_77320"]
_DEST_FLAGGED = ["acc_shell_77411209", "acc_proxy_30021", "acc_darknet_11900"]
_LOW_RISK_JX = ["US", "GB", "DE", "CA", "JP"]
_HIGH_RISK_JX = ["KY", "PA", "VG", "SC"]
_DEST_BICS = ["WFBIUS6SXXX", "BPCKCY22XXX", "OFFSVG00XXX", "CITIUS33XXX"]


async def run(service: FintechService, *, interval: float = 1.8) -> None:
    while True:
        await asyncio.sleep(interval * random.uniform(0.5, 1.5))
        suspicious = random.random() < 0.35
        payload = TransactionEvaluation(
            originating_account=random.choice(_ORIG_ACCOUNTS),
            originating_routing_bic=random.choice(_ORIG_BICS),
            destination_account=random.choice(_DEST_FLAGGED if suspicious else _DEST_NORMAL),
            destination_routing_bic=random.choice(_DEST_BICS),
            beneficiary_jurisdiction_country=random.choice(_HIGH_RISK_JX if suspicious else _LOW_RISK_JX),
            amount=round(random.uniform(50_000, 800_000) if suspicious else random.uniform(500, 25_000), 2),
            currency="USD",
            distinct_beneficiaries_count_1h=random.randint(3, 8) if suspicious else random.randint(0, 2),
            historical_max_single_tx_ratio=round(random.uniform(4.0, 9.0) if suspicious else random.uniform(0.5, 2.0), 1),
        )
        await service.evaluate(payload)
