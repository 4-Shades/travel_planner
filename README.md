# travel_planner
Travel planner project

## Documents

- [Software Requirements Specification](SOFTWARE_REQUIREMENTS_SPECIFICATION.md)
- [Test-Driven Development Plan](TEST_DRIVEN_DEVELOPMENT_PLAN.md)
- [Behavior Scenarios](BEHAVIOR_DRIVEN_DEVELOPMENT_SCENARIOS.md)
- [Implementation Guide](IMPLEMENTATION_GUIDE.md)

## Development

The agents target Python 3.11. Create a virtual environment and install the pinned dependencies:

```sh
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt   # Windows
.venv/bin/python -m pip install -r requirements-dev.txt       # macOS and Linux
```

Run the tests:

```sh
pytest tests
pytest features -m "not demonstration and not deployment"
```

The tests never reach a real network service: pytest-socket blocks every socket.

Run an agent. `APP_MODULE` names the agent's app: `agents.host.app:app`, `agents.flight.app:app`, `agents.stay.app:app`, or `agents.activities.app:app`.

```sh
uvicorn agents.host.app:app --log-config logging.json
```

Settings come from environment variables only: `LLM_TIMEOUT_SECONDS` (default 120), `DOWNSTREAM_TIMEOUT_SECONDS` (default 150, between `LLM_TIMEOUT_SECONDS` and 180), and `RAG_TOP_K` (default 2).

To change a dependency, edit `requirements.in` or `requirements-dev.in`, then recompile both lock files:

```sh
uv pip compile requirements.in --universal --python-version 3.11 -o requirements.txt
uv pip compile requirements-dev.in --universal --python-version 3.11 -o requirements-dev.txt
```
