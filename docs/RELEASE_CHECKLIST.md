# Release checklist

Requirements that tests cannot fully check in CI: the inspections and demonstrations in the TDD plan's §5, and the BDD scenarios tagged `@deployment` or `@demonstration`. Work through the list against a local stack and a Vercel preview before each release, and record the result and date in the last column.

## Automated before release

- [ ] CI is green on the release commit: Python unit and BDD tests, web unit tests, browser BDD and end-to-end tests, `npm audit`, and the secret scan.
- [ ] `tests/test_deployment.py` passes. It checks the Compose and Vercel configuration for TP-SRS-113, 142, 144, 161, 164 to 166, 183, and 188.
- [ ] `tests/test_repository.py::test_cloud_index_committed` passes instead of being skipped (TP-SRS-152).

## Self-hosted stack

| Requirement | Check | Result |
| --- | --- | --- |
| 164, 188 | `docker compose up -d` brings up every service with no paid service, and a trip planned at <http://localhost:3000> returns flights, stays, and activities. | |
| 113 | From another machine on the network, the specialists cannot be reached; only ports 3000 and 8000 answer. | |
| 144 | Plan a trip, wait 25 minutes, then run `docker compose exec ollama ollama ps`: both models are still loaded. (BDD: "Self-hosted models stay loaded") | |
| 085 | Stop the stack, remove the `guidance` volume, and start again without ingesting: plans still arrive, without sources, and the specialists' logs say why. | |
| 005 | One request with `X-Request-ID: release-check-1` appears with that ID in the logs of the Host and of all three specialists (`docker compose logs`). | |

## Vercel preview

| Requirement | Check | Result |
| --- | --- | --- |
| 140 | With functions warm, `POST /run` returns a plan within 10 s; after a fresh deployment (cold), within 30 s. Time five requests of each. (BDD: "Cloud plans arrive quickly with OpenAI") | |
| 141 | In the Host's logs, the three specialist calls start within the same second, and the plan's total time is close to the slowest of them. | |
| 165, 113 | Requests from outside to the specialists' own addresses fail; the web application and the Host's public routes answer. (BDD: "Only the web application and the Host are public") | |
| 184 | `curl -I http://<preview-domain>/` is redirected to HTTPS or refused. | |
| 110 | `POST /run` without `X-API-Key` returns 401; with it, 200. | |
| 042 | Search the page source and every script the browser loads for the `HOST_API_KEY` value; it is absent. | |
| 183 | Each service's environment, as Vercel shows it, holds only the secrets that service reads (docs/CONFIGURATION.md). Record any exception (docs/DEPLOYMENT.md). | |
| 120 | With `OTEL_EXPORTER_OTLP_ENDPOINT` set, request, model, token, and retrieval metrics appear in the metrics backend within two minutes. | |
| — | Each item in docs/DEPLOYMENT.md, "Open items to confirm on the first preview", is confirmed or resolved. | |

## Inspection

| Requirement | Check | Result |
| --- | --- | --- |
| 150 | Code review: no database, and no file written while handling a request. The "Data retention" BDD scenario passes. | |
| 160 to 163 | Next.js web application; Python 3.11 FastAPI agents in one codebase selected by `APP_MODULE`; contracts only in `shared/schemas.py`; configuration only from environment variables. | |
| 182 | No secret in source, Terraform state, or version control (secret scan), and `.env` files are excluded from Docker and Vercel uploads. | |
| 185 | CI workflows use no stored long-lived cloud keys. | |
| 186 | Switching `LLM_PROVIDER` or `RAG_STORE` needs only configuration. | |
| SRS §1.1 | `SOFTWARE_DESIGN_DOCUMENT.md` describes the Next.js interface. The SDD is not yet in this repository. | |
