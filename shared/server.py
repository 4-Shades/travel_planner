"""The FastAPI app every agent is built from (TP-SRS-001, TP-SRS-002, TP-SRS-006)."""

import logging

from fastapi import FastAPI

from shared.request_id import RequestIdMiddleware


def create_app(service, settings):
    """Return an app with the shared endpoints; the agent adds its own POST /run."""
    app = FastAPI(title=f"Travel planner {service} agent")
    app.state.settings = settings
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
