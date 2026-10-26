# travel_planner
Travel planner project

## Documents

- [Software Requirements Specification](docs/SOFTWARE_REQUIREMENTS_SPECIFICATION.md)
- [Test-Driven Development Plan](docs/TEST_DRIVEN_DEVELOPMENT_PLAN.md)
- [Behavior Scenarios](docs/BEHAVIOR_DRIVEN_DEVELOPMENT_SCENARIOS.md)
- [Implementation Guide](docs/IMPLEMENTATION_GUIDE.md)
- [HTTP API](docs/API.md), [Configuration](docs/CONFIGURATION.md), [Deployment](docs/DEPLOYMENT.md), and the [Release checklist](docs/RELEASE_CHECKLIST.md)

## Quick start

Run everything locally with Docker Compose, using Ollama, at no cost:

```sh
docker compose up -d ollama models && docker compose run --rm ingest && docker compose up -d
```

Then open http://localhost:3000. [Deployment](docs/DEPLOYMENT.md) covers this and the Vercel deployment.

## Development

The agents target Python 3.11. Create a virtual environment and install the pinned dependencies:

```sh
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements/requirements-dev.txt   # Windows
.venv/bin/python -m pip install -r requirements/requirements-dev.txt       # macOS and Linux
```

Run the tests:

```sh
pytest tests
pytest features -m "not demonstration and not deployment"
```

The tests never reach a real network service: pytest-socket blocks every socket.

Run the whole stack locally: the three specialists on ports 8001 to 8003, then the Host on 8000.

```sh
uvicorn agents.flight.app:app --port 8001 --log-config logging.json
uvicorn agents.stay.app:app --port 8002 --log-config logging.json
uvicorn agents.activities.app:app --port 8003 --log-config logging.json
uvicorn agents.host.app:app --port 8000 --log-config logging.json
```

Run one agent. `APP_MODULE` names the agent's app: `agents.host.app:app`, `agents.flight.app:app`, `agents.stay.app:app`, or `agents.activities.app:app`.

```sh
uvicorn agents.host.app:app --log-config logging.json
```

Settings come from environment variables only; [Configuration](docs/CONFIGURATION.md) lists them all, with which service reads each.

### Web application

The Next.js app in `web/` calls the Host from its server, never from the browser. It needs Node.js 20.9 or later.

```sh
cd web
npm ci
HOST_SERVICE_URL=http://localhost:8000 npm run dev   # then open http://localhost:3000
npm test                                            # unit tests
npm run test:bdd                                    # browser scenarios, against a fake Host
```

The web application reads `HOST_SERVICE_URL`, `HOST_API_KEY`, and `HOST_TIMEOUT_SECONDS`. `npm run test:bdd` also runs the end-to-end tests in `web/tests/e2e/`.

### Guidance index

Build or refresh the guidance index from Wikivoyage. The command embeds passages with the same settings as the agents, so the index matches them. Articles are cached in `data/rag/cache/` for 30 days.

```sh
python -m shared.rag.ingest                       # every destination in data/rag/destinations.txt
python -m shared.rag.ingest Tokyo NYC --refresh   # only these, downloaded again
python -m shared.rag.ingest --store file          # the cloud index; needs LLM_PROVIDER=openai
```

The self-hosted Chroma index (`data/rag/index/chroma/`) is not committed. The cloud index (`data/rag/index/file/`) is committed, because the cloud deployment bundles it.

The Chroma index needs the optional packages in `requirements/requirements-rag.txt` (included in `requirements/requirements-dev.txt`). Without them, or without an index, the specialists plan without guidance.

To change a dependency, edit a `.in` file in `requirements/`, then recompile the lock files in this order:

```sh
uv pip compile requirements/requirements.in --universal --python-version 3.11 -o requirements/requirements.txt
uv pip compile requirements/requirements-rag.in --universal --python-version 3.11 -o requirements/requirements-rag.txt
uv pip compile requirements/requirements-dev.in --universal --python-version 3.11 -o requirements/requirements-dev.txt
```
