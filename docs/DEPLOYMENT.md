# Deployment

The application runs self-hosted with Docker Compose, at no cost, or in the cloud on Vercel with OpenAI (TP-SRS-164, TP-SRS-188).

## Self-hosted: Docker Compose

Needs Docker with Compose, about 3 GB of disk for the models, and about 4 GB of free memory. No GPU is required.

```sh
cp .env.example .env               # optional: HOST_API_KEY and metrics settings
docker compose up -d ollama models # downloads qwen2.5:3b and nomic-embed-text once
docker compose run --rm ingest     # builds the Chroma guidance index from Wikivoyage
docker compose up -d               # Ollama, the four agents, and the web application
```

Then open <http://localhost:3000>. The Host's API is on <http://localhost:8000>. The specialists publish no ports: the Host reaches them on the Compose network (TP-SRS-113).

- **Rebuilding the index.** After changing `data/rag/destinations.txt`, run `docker compose run --rm ingest` again, then `docker compose restart flight stay activities`. The specialists open the index when they start.
- **Running without an index.** The specialists still plan, without guidance, and log why (TP-SRS-085).
- **Keeping models loaded.** Ollama keeps both models loaded for 30 minutes (`OLLAMA_KEEP_ALIVE=30m`, `OLLAMA_MAX_LOADED_MODELS=2`). Only the first plan after a quiet period pays the loading time (TP-SRS-144).
- **Timing on a CPU.** A plan takes one to two minutes (SRS §1.6).

## Cloud: Vercel

`vercel.json` defines one Vercel project with five services ([Vercel Services](https://vercel.com/kb/guide/vercel-services)):

| Service | Public routes | Reaches |
| --- | --- | --- |
| `web` (Next.js, `web/`) | everything else (`/`, `/api/plan`) | `host`, as `HOST_SERVICE_URL` |
| `host` (FastAPI) | `/run`, `/healthz`, `/readyz`, `/openapi.json`, `/docs` | the specialists, as `FLIGHT_SERVICE_URL`, `STAY_SERVICE_URL`, `ACTIVITIES_SERVICE_URL` |
| `flight`, `stay`, `activities` (FastAPI) | none: private, reached only through the Host's bindings (TP-SRS-165) | OpenAI |

Vercel injects each binding's URL when the service runs, so no service URLs are configured by hand.

### Before the first deployment

1. Build the cloud index with OpenAI embeddings and commit it (TP-SRS-152):
   `LLM_PROVIDER=openai OPENAI_API_KEY=… python -m shared.rag.ingest --store file`, then commit `data/rag/index/file/`.
2. Set these environment variables for Preview and Production:

   | Variable | Value |
   | --- | --- |
   | `LLM_PROVIDER` | `openai` |
   | `RAG_STORE` | `file` |
   | `RAG_INDEX_PATH` | `data/rag/index/file` |
   | `OPENAI_API_KEY` | the key (secret) |
   | `HOST_API_KEY` | a long random key (secret) |
   | `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS` | optional, for metrics |

3. Deploy a preview with `vercel deploy`, and work through the open items below and `docs/RELEASE_CHECKLIST.md`.

### Open items to confirm on the first preview

Vercel Services was in beta when this was written, and its documentation does not settle these points. Each needs checking on a preview deployment, and the configuration should be adjusted where needed.

| Item | Why it matters | What to check |
| --- | --- | --- |
| Python dependencies | Vercel looks for `requirements.txt` or `pyproject.toml` at a Python service's root (`./`). The pinned lock files are in `requirements/`. | The build log installs the pins from `requirements/requirements.txt`. If not, give the Python services a root-level dependency file generated from that lock. |
| Python version | The SRS requires Python 3.11 (TP-SRS-161); Vercel's Python guides mention 3.12 and later. | The build log's Python version. The test suite runs on 3.11; if Vercel uses a later version, run the suite on that version too and record the difference. |
| Function duration | The web route waits up to 180 s for the Host, and the Host up to 150 s for a specialist (TP-SRS-142, SRS §1.7). | Each service's maximum duration is above those waits. `web/app/api/plan/route.ts` sets `maxDuration = 190`. |
| Secrets by service | Vercel scopes environment variables by environment, not by service, so every service may receive every secret (TP-SRS-183). | Whether Services can scope variables per service. If not, record the exception, or split the specialists into their own project. |
| Bundle size | The specialists bundle the index; SRS §1.3.6 estimates about 226 MB. | The deployment succeeds within the function size limit. |
| HTTPS | All public traffic must use HTTPS (TP-SRS-184). | `http://` requests are redirected or refused. |

## Continuous integration

`.github/workflows/ci.yml` runs every Python, web, and browser test on each push and pull request to `main`, plus `npm audit` and a secret scan. It uses no stored cloud keys (TP-SRS-185). A deployment job that needs cloud access should authenticate through OpenID Connect.
