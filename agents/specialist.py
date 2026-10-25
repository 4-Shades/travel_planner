"""The Flight, Stay, and Activities agents, built from one factory."""

from shared.config import Settings
from shared.schemas import SPECIALISTS, TravelRequest
from shared.server import create_app

UNAVAILABLE = {
    "flight": "Flight planner is temporarily unavailable.",
    "stay": "Stay planner is temporarily unavailable.",
    "activities": "Activity planner is temporarily unavailable.",
}


def create_specialist_app(service, settings=None):
    settings = settings or Settings.from_env()
    contract = SPECIALISTS[service]
    app = create_app(service, settings)

    @app.post("/run", response_model=contract.response)
    async def run(request: TravelRequest):
        # Placeholder until phase 6 asks the language model for suggestions.
        return contract.response(error=UNAVAILABLE[service])

    return app
