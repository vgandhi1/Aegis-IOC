"""Async event bus + WebSocket broadcaster.

Implements the transport-optimization rules from the spec:

* Cyber  — buffered batch flush every ``cyber_flush_ms`` (default 250ms).
* FinTech — buffered, but high-risk items are flushed immediately (<50ms).
* Health  — buffered with a slow heartbeat (default 500ms).

A channel is a domain name ("cyber" | "health" | "fintech"). Each channel keeps
a set of connected websockets and a pending buffer drained by a flush loop.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

from fastapi import WebSocket


class Channel:
    def __init__(self, name: str, flush_ms: int) -> None:
        self.name = name
        self.flush_interval = max(flush_ms, 1) / 1000.0
        self.connections: set[WebSocket] = set()
        self.buffer: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self.connections.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self.connections.discard(ws)

    async def _send(self, payload: dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self.connections)
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self.connections.discard(ws)

    async def publish(self, message: dict[str, Any], *, immediate: bool = False) -> None:
        if immediate:
            await self._send({"channel": self.name, "batch": [message]})
            return
        async with self._lock:
            self.buffer.append(message)

    async def flush_once(self) -> None:
        async with self._lock:
            if not self.buffer:
                return
            batch = self.buffer
            self.buffer = []
        await self._send({"channel": self.name, "batch": batch})


class Broadcaster:
    def __init__(self) -> None:
        self._channels: dict[str, Channel] = {}
        self._tasks: list[asyncio.Task] = []
        self._running = False

    def register(self, name: str, flush_ms: int) -> Channel:
        channel = Channel(name, flush_ms)
        self._channels[name] = channel
        return channel

    def channel(self, name: str) -> Channel:
        if name not in self._channels:
            raise KeyError(f"Unknown channel: {name}")
        return self._channels[name]

    async def publish(self, name: str, message: dict[str, Any], *, immediate: bool = False) -> None:
        await self.channel(name).publish(message, immediate=immediate)

    async def _flush_loop(self, channel: Channel) -> None:
        while self._running:
            await asyncio.sleep(channel.flush_interval)
            with contextlib.suppress(Exception):
                await channel.flush_once()

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        for channel in self._channels.values():
            self._tasks.append(asyncio.create_task(self._flush_loop(channel)))

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._tasks.clear()
