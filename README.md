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
| `RAG_TOP_K` | 2 | Guidance passages per prompt |
| `HOST_API_KEY` | none | When set, the Host's `POST /run` requires a matching `X-API-Key` header |

To change a dependency, edit `requirements.in` or `requirements-dev.in`, then recompile both lock files:

```sh
uv pip compile requirements.in --universal --python-version 3.11 -o requirements.txt
uv pip compile requirements-dev.in --universal --python-version 3.11 -o requirements-dev.txt
```
