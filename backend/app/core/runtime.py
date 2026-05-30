"""Process-wide runtime wiring.

Holds the broadcaster, per-domain stores, and domain services. Instantiated once
in the app factory and attached to ``app.state.runtime`` so routes and
simulators share the same instances.
"""

from __future__ import annotations

from ..config import Settings
from .events import Broadcaster
from .store import RingStore


class Runtime:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.broadcaster = Broadcaster()

        # one channel per domain, each with its own flush cadence
        self.broadcaster.register("cyber", settings.cyber_flush_ms)
        self.broadcaster.register("fintech", settings.fintech_flush_ms)
        self.broadcaster.register("health", settings.health_heartbeat_ms)

        self.cyber_store = RingStore(settings.store_capacity)
        self.fintech_store = RingStore(settings.store_capacity)
        self.health_store = RingStore(settings.store_capacity)

        # services are attached lazily to avoid import cycles
        self.cyber = None
        self.health = None
        self.fintech = None
