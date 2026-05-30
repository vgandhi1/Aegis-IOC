"""Aegis IOC backend application factory.

Wires the gateway middleware, auth + domain routers, WebSocket streams, the
shared runtime (broadcaster + stores + services), and the background simulators.
"""

from __future__ import annotations

import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .auth.routes import router as auth_router
from .config import get_settings
from .core.runtime import Runtime
from .domains.cyber import simulator as cyber_sim
from .domains.cyber.routes import router as cyber_router
from .domains.cyber.service import CyberService
from .domains.fintech import simulator as fintech_sim
from .domains.fintech.routes import router as fintech_router
from .domains.fintech.service import FintechService
from .domains.health import simulator as health_sim
from .domains.health.routes import router as health_router
from .domains.health.service import HealthService
from .ws.routes import router as ws_router

API_PREFIX = "/api/v1"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Gateway-style hardening headers applied to every response."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; frame-ancestors 'none'; object-src 'none'",
        )
        return response


def _build_runtime(app: FastAPI) -> Runtime:
    settings = get_settings()
    runtime = Runtime(settings)
    runtime.cyber = CyberService(runtime.cyber_store, runtime.broadcaster)
    runtime.health = HealthService(runtime.health_store, runtime.broadcaster)
    runtime.fintech = FintechService(runtime.fintech_store, runtime.broadcaster)
    app.state.runtime = runtime
    return runtime


@asynccontextmanager
async def lifespan(app: FastAPI):
    runtime = _build_runtime(app)
    runtime.broadcaster.start()

    sim_tasks: list[asyncio.Task] = []
    if runtime.settings.enable_simulators:
        sim_tasks = [
            asyncio.create_task(cyber_sim.run(runtime.cyber)),
            asyncio.create_task(health_sim.run(runtime.health)),
            asyncio.create_task(fintech_sim.run(runtime.fintech)),
        ]
    try:
        yield
    finally:
        for task in sim_tasks:
            task.cancel()
        for task in sim_tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        await runtime.broadcaster.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=f"{settings.app_name} API",
        version="1.0.0",
        description="Tri-domain Institutional Operations Center — gateway + cyber/health/fintech services.",
        lifespan=lifespan,
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Auth + domain routers mounted behind the /api/v1 gateway prefix.
    app.include_router(auth_router, prefix=API_PREFIX)
    app.include_router(cyber_router, prefix=API_PREFIX)
    app.include_router(health_router, prefix=API_PREFIX)
    app.include_router(fintech_router, prefix=API_PREFIX)
    app.include_router(ws_router)

    @app.get("/health", tags=["meta"])
    async def healthcheck() -> dict:
        return {"status": "ok", "service": settings.app_name, "environment": settings.environment}

    return app


app = create_app()
