"""The Host agent: the only agent clients call (APP_MODULE=agents.host.app:app).

It calls the specialists and never a language model (TP-SRS-066).
"""

from agents.host.planner import SERVICE_UNAVAILABLE, plan_trip
from shared.config import Settings
from shared.schemas import TravelRequest, TripPlan
from shared.server import create_app

__all__ = ["SERVICE_UNAVAILABLE", "app", "create_host_app"]


def create_host_app(settings=None, metrics=None):
    settings = settings or Settings.from_env()
    app = create_app("host", settings, api_key=settings.host_api_key, metrics=metrics)

    @app.post("/run", response_model=TripPlan)
    async def run(request: TravelRequest):
        # Status 200 for every valid request, even when some or all specialists failed (TP-SRS-064).
        return await plan_trip(request, settings)

    return app


app = create_host_app()
