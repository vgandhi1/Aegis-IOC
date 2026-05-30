"""In-memory ring-buffer store.

Reference stand-in for the production datastores (ClickHouse / FHIR /
CockroachDB). Keeps the most recent ``capacity`` records per domain and supports
id lookups and simple patching (used by remediation / override actions).

Swap this module for a real persistence layer without touching the domain
services that depend on its interface.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any


class RingStore:
    def __init__(self, capacity: int = 5000) -> None:
        self._capacity = capacity
        self._items: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
        self._lock = threading.RLock()

    def add(self, key: str, record: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._items[key] = record
            self._items.move_to_end(key)
            while len(self._items) > self._capacity:
                self._items.popitem(last=False)
        return record

    def get(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            return self._items.get(key)

    def patch(self, key: str, changes: dict[str, Any]) -> dict[str, Any] | None:
        with self._lock:
            record = self._items.get(key)
            if record is None:
                return None
            record.update(changes)
            return record

    def latest(self, limit: int = 200) -> list[dict[str, Any]]:
        with self._lock:
            values = list(self._items.values())
        return list(reversed(values[-limit:]))

    def __len__(self) -> int:  # pragma: no cover - trivial
        with self._lock:
            return len(self._items)
