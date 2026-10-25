"""The Host agent: the only agent clients call (APP_MODULE=agents.host.app:app)."""

from typing import get_args

from shared.config import Settings
from shared.schemas import Part, PartError, TravelRequest, TripPlan
from shared.server import create_app

SERVICE_UNAVAILABLE = "Service is temporarily unavailable."


def create_host_app(settings=None):
    settings = settings or Settings.from_env()
    app = create_app("host", settings, api_key=settings.host_api_key)

    @app.post("/run", response_model=TripPlan)
    async def run(request: TravelRequest):
        # Placeholder until phase 9 calls the specialists: every part is reported as unavailable.
        return TripPlan(
            request_id=request.request_id,
            trip_id=request.trip_id,
            errors=[PartError(part=part, message=SERVICE_UNAVAILABLE) for part in get_args(Part)],
        )

    return app


app = create_host_app()
