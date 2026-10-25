"""The FastAPI app every agent is built from (TP-SRS-001, TP-SRS-002, TP-SRS-006)."""

import logging

from fastapi import FastAPI

from shared.auth import ApiKeyMiddleware
from shared.request_id import RequestIdMiddleware


def create_app(service, settings, api_key=None):
    """Return an app with the shared endpoints; the agent adds its own POST /run.

    With an api_key, POST /run requires a matching X-API-Key header.
    """
    app = FastAPI(title=f"Travel planner {service} agent")
    app.state.settings = settings
    # Middleware added last runs first: request IDs are set before the key is checked,
    # so rejected requests are logged with their ID too.
    if api_key:
        app.add_middleware(ApiKeyMiddleware, api_key=api_key)
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
