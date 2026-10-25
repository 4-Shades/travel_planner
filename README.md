# travel_planner
Travel planner project

## Documents

- [Software Requirements Specification](docs/SOFTWARE_REQUIREMENTS_SPECIFICATION.md)
- [Test-Driven Development Plan](docs/TEST_DRIVEN_DEVELOPMENT_PLAN.md)
- [Behavior Scenarios](docs/BEHAVIOR_DRIVEN_DEVELOPMENT_SCENARIOS.md)
- [Implementation Guide](docs/IMPLEMENTATION_GUIDE.md)

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

Settings come from environment variables only:

| Variable | Default | Meaning |
| --- | --- | --- |
| `LLM_PROVIDER` | `ollama` | `ollama` or `openai` |
| `LLM_MODEL` | `qwen2.5:3b` (Ollama), `gpt-4.1-mini` (OpenAI) | Chat model; it must accept temperature 0 |
| `EMBEDDING_MODEL` | `nomic-embed-text` (Ollama), `text-embedding-3-small` (OpenAI) | Embedding model |
| `EMBEDDING_DIMENSIONS` | 768 (Ollama), 1536 (OpenAI) | Vector size the embedding model returns |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama address |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI address |
| `OPENAI_API_KEY` | none | Required by agents that call OpenAI |
| `LLM_TIMEOUT_SECONDS` | 120 | Longest wait for one model call |
| `DOWNSTREAM_TIMEOUT_SECONDS` | 150 | Longest wait for a specialist; between `LLM_TIMEOUT_SECONDS` and 180 |
| `RAG_ENABLED` | `true` | Add Wikivoyage guidance to the specialists' prompts |
| `RAG_STORE` | `chroma` | Guidance index type: `chroma` (self-hosted) or `file` (cloud) |
| `RAG_INDEX_PATH` | `data/rag/index/<store>` | Guidance index location |
| `RAG_DESTINATIONS_FILE` | `data/rag/destinations.txt` | Destinations and their aliases, one per line: `New York City \| NYC` |
| `RAG_TOP_K` | 2 | Guidance passages per prompt |
| `RAG_TIMEOUT_SECONDS` | 5 | Longest wait for a guidance lookup; after it, the agent plans without guidance |
| `HOST_API_KEY` | none | When set, the Host's `POST /run` requires a matching `X-API-Key` header |
| `FLIGHT_SERVICE_URL` | `http://localhost:8001` | Where the Host finds the Flight agent |
| `STAY_SERVICE_URL` | `http://localhost:8002` | Where the Host finds the Stay agent |
| `ACTIVITIES_SERVICE_URL` | `http://localhost:8003` | Where the Host finds the Activities agent |

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
