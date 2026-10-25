"""The Activities agent (APP_MODULE=agents.activities.app:app)."""

from agents.specialist import create_specialist_app

app = create_specialist_app("activities")
