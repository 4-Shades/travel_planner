"""The Flight agent (APP_MODULE=agents.flight.app:app)."""

from agents.specialist import create_specialist_app

app = create_specialist_app("flight")
