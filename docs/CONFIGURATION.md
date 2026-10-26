# Configuration

All configuration comes from environment variables; nothing is read from a file (TP-SRS-163). An empty value counts as not set. An unusable value stops the service at startup with a message naming the variable.

## Agents

"Reads" shows which agents use each variable; give a service only the secrets it reads (TP-SRS-183).

| Variable | Default | Reads | Meaning |
| --- | --- | --- | --- |
| `APP_MODULE` | `agents.host.app:app` (image) | all | Which agent the image runs: `agents.{host,flight,stay,activities}.app:app` |
| `LLM_PROVIDER` | `ollama` | specialists | `ollama` or `openai` |
| `LLM_MODEL` | `qwen2.5:3b` / `gpt-4.1-mini` | specialists | Chat model; must accept temperature 0 |
| `EMBEDDING_MODEL` | `nomic-embed-text` / `text-embedding-3-small` | specialists | Embedding model |
| `EMBEDDING_DIMENSIONS` | 768 / 1536 | specialists | The embedding model's vector size |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | specialists | Ollama's address |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | specialists | OpenAI's address |
| `OPENAI_API_KEY` | none | specialists, when `LLM_PROVIDER=openai` | **Secret.** Never give it to the Host. |
| `LLM_TIMEOUT_SECONDS` | 120 | specialists | Longest wait for one model call |
| `RAG_ENABLED` | `true` | specialists | Add Wikivoyage guidance to prompts |
| `RAG_STORE` | `chroma` | specialists | `chroma` (self-hosted) or `file` (cloud) |
| `RAG_INDEX_PATH` | `data/rag/index/<store>` | specialists | Guidance index location |
| `RAG_DESTINATIONS_FILE` | `data/rag/destinations.txt` | specialists | Destinations and aliases |
| `RAG_TOP_K` | 2 | specialists | Guidance passages per prompt |
| `RAG_TIMEOUT_SECONDS` | 5 | specialists | Longest wait for a guidance lookup |
| `FLIGHT_SERVICE_URL`, `STAY_SERVICE_URL`, `ACTIVITIES_SERVICE_URL` | `http://localhost:8001` to `8003` | Host | Where the specialists are |
| `DOWNSTREAM_TIMEOUT_SECONDS` | 150 | Host | Longest wait for a specialist; must be greater than `LLM_TIMEOUT_SECONDS` and less than 180 (TP-SRS-142) |
| `HOST_API_KEY` | none | Host | **Secret.** When set, `POST /run` requires it in `X-API-Key`. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | none | all agents | When set, metrics are pushed over OTLP/HTTP every minute (TP-SRS-120) |
| `OTEL_EXPORTER_OTLP_HEADERS` | none | all agents | **Secret.** Headers for the metrics endpoint, such as Grafana Cloud's `Authorization` |

The model defaults change with `LLM_PROVIDER`: the first value is for Ollama, the second for OpenAI. The Host never reads the model or retrieval settings, because it never calls a model (TP-SRS-066).

## Web application

| Variable | Default | Meaning |
| --- | --- | --- |
| `HOST_SERVICE_URL` | none | The Host's address. Read on the server only (TP-SRS-041). |
| `HOST_API_KEY` | none | **Secret.** Sent to the Host as `X-API-Key`; never sent to the browser (TP-SRS-042). |
| `HOST_TIMEOUT_SECONDS` | 180 | Longest wait for the Host (TP-SRS-022) |

## Ingest command

`python -m shared.rag.ingest` uses the agents' model and retrieval settings, so the index it builds matches the specialists that read it. Its own options (`--store`, `--index-path`, `--destinations-file`, `--cache-dir`, `--refresh`, `--contact-url`) are listed by `python -m shared.rag.ingest --help`. A file (cloud) index needs `LLM_PROVIDER=openai` (TP-SRS-106).

## Secrets by service

| Secret | Self-hosted (Docker Compose) | Cloud (Vercel) |
| --- | --- | --- |
| `HOST_API_KEY` | Host, web | Host, web |
| `OPENAI_API_KEY` | none (Ollama is used) | specialists |
| `OTEL_EXPORTER_OTLP_HEADERS` | all agents | all agents |

Secrets are never committed: `.env` files and Terraform state are ignored by git, Docker, and Vercel (TP-SRS-182). Copy `.env.example` to `.env` for Docker Compose.
