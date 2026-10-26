"""The FastAPI app every agent is built from (TP-SRS-001, TP-SRS-002, TP-SRS-006)."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from shared.auth import ApiKeyMiddleware
from shared.request_id import RequestIdMiddleware
from shared.telemetry import MetricsMiddleware, create_metrics


def create_app(service, settings, api_key=None, metrics=None):
    """Return an app with the shared endpoints; the agent adds its own POST /run.

    With an api_key, POST /run requires a matching X-API-Key header. Metrics are set up from
    the settings unless given.
    """
    metrics = metrics or create_metrics(service, settings)

    @asynccontextmanager
    async def lifespan(app):
        yield
        # Sends the last measurements before the process ends.
        metrics.shutdown()

    app = FastAPI(title=f"Travel planner {service} agent", lifespan=lifespan)
    app.state.settings = settings
    app.state.metrics = metrics
    # Middleware added last runs first: request IDs are set before the key is checked,
    # so rejected requests are logged with their ID too.
    if api_key:
        app.add_middleware(ApiKeyMiddleware, api_key=api_key)
    app.add_middleware(MetricsMiddleware, metrics=metrics, routes=lambda: {route.path for route in app.routes})
    app.add_middleware(RequestIdMiddleware, logger=logging.getLogger(f"travel_planner.{service}"))

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok", "service": service}

    @app.get("/readyz")
    async def readyz():
        return {"status": "ready", "service": service}

    @app.get("/")
    async def root():
        return {"service": service, "docs": "/docs", "openapi": "/openapi.json"}

    return app
