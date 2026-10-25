# Implementation Guide: ADK-Powered Travel Planner

| Field | Value |
| --- | --- |
| Project | ADK-Powered Travel Planner |
| Document | Implementation guide |
| Version | 1.0.0 |
| Date | October 25, 2026 |
| Author | Chaim Joseph Cordova |
| Status | Draft |

**Revision history**

| Name | Date | Reason for changes | Version |
| --- | --- | --- | --- |
| Chaim Joseph Cordova | October 25, 2026 | First version, derived from SRS 1.0.0, TDD plan 1.0.0, and BDD scenarios 1.0.0 | 1.0.0 |

**Contents:** 1. Introduction · 2. Working rules · 3. Phase overview · 4. Phases · 5. Requirements by phase · 6. Open decisions · 7. References

## 1. Introduction

### 1.1 Purpose

This guide splits the build of the travel planner into twelve phases. Each phase delivers a working, tested slice of the system, and each one depends only on earlier phases.

### 1.2 Source documents

| Document | What it gives this guide |
| --- | --- |
| [SRS] | *What* to build: requirements `TP-SRS-001` to `TP-SRS-188` |
| [TDD] | *How* to drive the code: unit and service tests by ID (`SCH-01`, `HST-05`, …), test doubles, and fixtures |
| [BDD] | *How to accept* it: Gherkin features, tagged by requirement |

This guide uses the IDs from those documents unchanged. It adds no new requirements or tests. Where a phase needs work no automated test covers (for example, Docker Compose), the phase lists it as a manual check.

### 1.3 How to read a phase

Each phase in §4 uses the same template:

- **Goal**: what exists at the end of the phase.
- **Requirements**: the SRS IDs the phase delivers in full (see §5), and any it starts.
- **Tests**: the TDD test IDs to write, in order.
- **Files**: representative paths. Paths that depend on an open decision (§6) are marked †.
- **Steps**: the order of work.
- **BDD**: the features that go green, and where their step definitions live.
- **Exit criteria**: what must be true before the next phase starts.
- **Commit**: a suggested commit message.

Requirement IDs are shortened in tables: `050` means **TP-SRS-050**.

## 2. Working rules

1. **Test first.** Follow the red–green–refactor cycle in [TDD] §2.1 for every TDD test ID in the phase. Write the test, watch it fail for the expected reason, write the least code that passes, then tidy.
2. **BDD alongside.** Write the step definitions for a phase's features in the same phase as the code they exercise. A scenario that cannot pass yet is not bound early. It stays unbound until its phase.
3. **Everything green.** A phase is finished only when the whole suite passes, not just the phase's new tests. CI runs it on every push and pull request to `main`.
4. **No external services.** No automated test reaches Ollama, OpenAI, MediaWiki, an OTLP endpoint, or a real agent over the network (TP-SRS-187). The socket guard from phase 1 enforces this.
5. **Settle decisions first.** Before starting a phase, settle the open decisions §6 assigns to it, and update [TDD] §7 if a decision differs from the assumption written there.
6. **Review before push.** At the end of each phase, the changes go to the project owner for review together with a suggested commit message. The owner commits and pushes them.

Standard commands, used in the exit criteria:

| Command | Runs |
| --- | --- |
| `pytest tests` | Python unit and service tests |
| `pytest features -m "not demonstration and not deployment"` | Python BDD scenarios |
| `npm test --prefix web` | Web unit tests (Vitest) |
| `npx playwright test` (in `web/`) | Web BDD and end-to-end tests |

## 3. Phase overview

| # | Phase | Delivers | TDD tests | BDD features | Depends on |
| --- | --- | --- | --- | --- | --- |
| 1 | Repository foundation | 166, 182, 185, 187 | REP-01, REP-02 | none (harness only) | none |
| 2 | Data contracts | 050–053, 074, 162, 172 | SCH-01–19 | none | 1 |
| 3 | Configuration and agent HTTP shell | 001, 002, 004, 006, 161, 163 | CFG-01, CFG-04–07, SRV-01–07 | Agent service endpoints (partial); Performance: timeouts must nest | 2 |
| 4 | API protection | 110–112 | KEY-01–07 | API protection (except `@deployment`) | 3 |
| 5 | Model clients | 071, 077 | CFG-02, CFG-03, LLM-01–08 | none | 3 |
| 6 | Specialist planning | 070, 072, 073, 075, 076 | SPC-01–11 | Suggestion generation | 5 |
| 7 | Guidance retrieval | 080–082, 084–090, 143, 151, 181, 186 | CFG-08, RAG-01–23 | Guidance retrieval | 6 |
| 8 | Guidance ingest | 083, 100–107, 152, 171 | ING-01–14, REP-03 | Guidance index management | 7 |
| 9 | Host orchestration | 003, 005, 060–066, 141, 150, 180 | SRV-08, HST-01–10 | Trip planning; Travel request validation; Data retention; Agent service endpoints (rest) | 4, 6 |
| 10 | Metrics | 120–122 | TEL-01–07 | Metrics | 9 |
| 11 | Web application | 010–015, 020–022, 030–033, 040, 041, 043, 130, 132, 142, 160, 170 | WEB-R01–08, WEB-F01–07, WEB-P01–04, WEB-T01–05 | Trip form; Planning progress; Results display; Server-side access to the Host (partial) | 9 |
| 12 | End-to-end, deployment, and release | 042, 113, 131, 133, 140, 144, 164, 165, 183, 184, 188 | E2E-01–06 | Usability; Server-side access to the Host (rest); all `@deployment` and `@demonstration` scenarios | 8, 10, 11 |

Phases 4 and 5 both depend only on phase 3, so they can be built in either order. Every other phase follows the numbering.

## 4. Phases

### Phase 1: Repository foundation

**Goal.** An empty but fully wired project: pinned dependencies, the test harness with its fakes and socket guard, ignore files, and CI.

**Requirements.** Delivers 166, 182, 185, 187.

**Tests.** REP-01, REP-02. Also the socket guard from [TDD] §2.1, which the whole suite relies on.

**Files.**
- `pyproject.toml`, `requirements.txt`, `requirements-dev.txt` (exact `==` pins, Python 3.11)
- `tests/conftest.py` (the fixtures `valid_request`, `settings`, and `today`, and the socket guard)
- `tests/fakes/__init__.py`, `tests/fakes/llm.py`, `tests/fakes/agents.py` (empty modules for the [TDD] §2.3 doubles, filled in by later phases)
- `tests/test_repository.py`
- `features/conftest.py`
- `.gitignore`, `.dockerignore`, `.vercelignore`
- `.github/workflows/ci.yml`

**Steps.**
1. Settle the phase 1 decision in §6 (web application location), since CI paths depend on it.
2. Pin runtime dependencies (FastAPI, Uvicorn, pydantic, httpx) and dev dependencies (pytest, pytest-asyncio, pytest-socket, pytest-bdd, respx, freezegun). Write REP-01 and make it pass. Until phase 11 the `package.json` part of REP-01 is skipped, because the file doesn't exist yet.
3. Write REP-02, then add the ignore files so that `.env*` and Terraform state are excluded from git, Docker, and Vercel.
4. Add the socket guard (`--disable-socket --allow-unix-socket`) to the pytest configuration. Write a throwaway test that opens a real connection, and confirm the guard fails it.
5. Register the pytest markers used by BDD tags (`web`, `api`, `host`, `specialist`, `rag`, `ingest`, `metrics`, `demonstration`, `deployment`) so that `-m` filters work.
6. Add the CI workflow: run `pytest tests` and `pytest features -m "not demonstration and not deployment"` on push and pull request to `main`. Any cloud access added later uses OpenID Connect federation, never stored keys (185). Add a secret scanner such as gitleaks.

**BDD.** No features yet. `features/conftest.py` holds shared steps such as "a valid travel request" (see [BDD] §2.2).

**Exit criteria.**
- `pytest tests` passes (REP-01, REP-02).
- CI runs green on a pull request.
- A test that opens a real socket fails.

**Commit.**
```
Set up project skeleton, pinned dependencies, test harness, and CI

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

### Phase 2: Data contracts

**Goal.** Every data contract between services is defined once, in `shared/schemas.py`, with all validation and normalization rules.

**Requirements.** Delivers 050–053, 074, 162, 172. Starts 062, 070, 089, and 090 (the models exist; the behavior around them is finished in later phases).

**Tests.** SCH-01 to SCH-19, in order.

**Files.**
- `shared/__init__.py`, `shared/schemas.py`
- `tests/test_schemas.py`

**Steps.**
1. Settle the phase 2 decision in §6 (shape of an `errors` entry).
2. **Travel request** (SCH-01 to SCH-14). Field limits, date order, currency format, preference and `user_id` limits, collapsing repeated spaces, upper-casing the currency, generated UUIDs, and `USD` as the default currency. Use ISO 8601 dates.
3. **Trip plan** (SCH-15). Exactly `request_id`, `trip_id`, `flights`, `stay`, `activities`, `errors`, and `sources`.
4. **Specialist responses** (SCH-16, SCH-17). One model per specialist, each needing at least one offer or an `error`. Offer prices are zero or more, with a three-letter currency.
5. **Sources** (SCH-18). A source needs a title, a URL, and a license.
6. **Model-facing schemas** (SCH-19). Build the JSON schema given to the language model separately from the response model, so that it has no `sources` field.

**BDD.** None. The validation scenarios need a running Host and go green in phase 9.

**Exit criteria.**
- `pytest tests` passes.
- No other module defines a contract between services (162).

**Commit.**
```
Define shared request, plan, offer, and source schemas

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

### Phase 3: Configuration and agent HTTP shell

**Goal.** All four agents start from one codebase, read their settings from the environment, and serve the standard endpoints. The Host's `POST /run` validates the request and returns a placeholder plan.

**Requirements.** Delivers 001, 002, 004, 006, 161, 163. Starts 005 (request IDs in logs), 080 (`RAG_TOP_K` default), and 142 (timeout nesting in configuration).

**Tests.** CFG-01, CFG-04, CFG-05, CFG-06, CFG-07, then SRV-01 to SRV-07. CFG-02 and CFG-03 wait for phase 5, CFG-08 for phase 7, and SRV-08 for phase 9.

**Files.**
- `shared/config.py` (settings from environment variables, timeout nesting check)
- `shared/server.py` (FastAPI app factory, `X-Request-ID` logging middleware)
- `agents/host/app.py`, `agents/flight/app.py`, `agents/stay/app.py`, `agents/activities/app.py`
- `tests/test_config.py`, `tests/test_a2a_server.py`
- `features/api/agent_endpoints.feature`, `features/operations/performance.feature`, `features/steps/test_agent_endpoints.py`

**Steps.**
1. Settle the phase 3 decision in §6 (service names reported by `/healthz`).
2. Write CFG-01, CFG-04, CFG-05, and CFG-06. All settings come only from environment variables. Startup fails if `DOWNSTREAM_TIMEOUT_SECONDS` is not greater than `LLM_TIMEOUT_SECONDS` and less than 180.
3. Write CFG-07. `APP_MODULE` selects which of the four agents starts.
4. Write SRV-01 to SRV-07 against the app factory: `POST /run`, `GET /healthz`, `GET /readyz`, `GET /`, and `GET /openapi.json`; 422 responses listing the invalid fields; and the request ID in every log line.
5. The Host's `POST /run` validates the travel request and returns a placeholder trip plan with empty parts. The specialists' `POST /run` validates the request and returns a placeholder error. Phases 6 and 9 replace these placeholders.

**BDD.** From [BDD] §4.1, "Agent service endpoints": every scenario except "A request ID is logged and forwarded to every specialist", which waits for phase 9. From [BDD] §6.2, "Performance": the "Timeouts must nest" outline.

**Exit criteria.**
- `pytest tests` and `pytest features -m "not demonstration and not deployment"` pass.
- `uvicorn agents.host.app:app --log-config logging.json` starts locally, `GET /healthz` answers, and log lines show the request ID. `APP_MODULE` holds this import string.

**Commit.**
```
Add environment configuration and the shared agent HTTP shell

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

### Phase 4: API protection

**Goal.** The Host's public `POST /run` requires a matching key whenever `HOST_API_KEY` is set.

**Requirements.** Delivers 110, 111, 112. Starts 132 (the 401 message reveals nothing).

**Tests.** KEY-01 to KEY-07.

**Files.**
- `shared/auth.py` (FastAPI dependency)
- `tests/test_a2a_server.py` (key section)
- `features/api/api_protection.feature`, `features/steps/test_api_protection.py`

**Steps.**
1. Settle the phase 4 decision in §6 (the key is checked before the body).
2. Write KEY-01 to KEY-04 and KEY-06. Add a dependency that compares the `X-API-Key` header with `HOST_API_KEY` and is applied only to the Host's `POST /run`. `/healthz` stays open (SRV-03 must still pass).
3. Write KEY-05. Make the comparison with `hmac.compare_digest`.
4. Write KEY-07. The 401 body is a fixed plain sentence.

**BDD.** From [BDD] §4.5, "API protection": every scenario except the `@deployment` one. "Answers normally" scenarios pass against the phase 3 placeholder plan.

**Exit criteria.** `pytest tests` and the BDD command pass.

**Commit.**
```
Require a matching X-API-Key on the Host when HOST_API_KEY is set

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

### Phase 5: Model clients

**Goal.** Clients for Ollama and OpenAI that request schema-constrained JSON at temperature 0, report token usage, create embeddings, and turn every failure into one error type.

**Requirements.** Delivers 071, 077. Starts 073 (client errors), 085 and 086 (embedding sizes), and 120 (token counts).

**Tests.** CFG-02, CFG-03, then LLM-01 to LLM-08.

**Files.**
- `shared/llm/__init__.py` (provider factory and the shared error type)
- `shared/llm/ollama_client.py`, `shared/llm/openai_client.py`
- `tests/fakes/llm.py` (`FakeLLM`, `FakeEmbedder`)
- `tests/test_ollama_client.py`, `tests/test_openai_client.py`

**Steps.**
1. Settle the phase 5 decision in §6 (an unknown provider stops startup).
2. Build `FakeLLM` and `FakeEmbedder` as respx routes ([TDD] §2.3).
3. Write CFG-02 and CFG-03, then the provider factory selected by `LLM_PROVIDER`.
4. Write LLM-01, LLM-03, LLM-04, LLM-06, and LLM-07 for Ollama (`/api/chat` with `format` set to the schema, `options.temperature` 0, `stream` false).
5. Write LLM-02 to LLM-07 for OpenAI (`response_format` of type `json_schema` with `strict: true`, `temperature` 0, refusals treated as errors).
6. Write LLM-08 for both embedding clients.

**BDD.** None. The clients are exercised by the Suggestion generation feature in phase 6.

**Exit criteria.** `pytest tests` passes with the socket guard on.

**Commit.**
```
Add Ollama and OpenAI clients with strict JSON output and embeddings

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

### Phase 6: Specialist planning

**Goal.** The Flight, Stay, and Activities agents produce validated offers from the language model, or a fixed plain error. Retrieval is still off.

**Requirements.** Delivers 070, 072, 073, 075, 076. Continues 132 (no internal detail in error responses).

**Tests.** SPC-01 to SPC-11.

**Files.**
- `agents/specialist.py` (shared planning flow: build prompt, call model, validate, map failures)
- `agents/flight/prompt.py`, `agents/stay/prompt.py`, `agents/activities/prompt.py`
- `tests/test_specialists.py`
- `features/api/suggestion_generation.feature`, `features/steps/test_suggestion_generation.py`

**Steps.**
1. Write SPC-01 and SPC-08. The shared flow sends the agent's response schema from `shared/schemas.py` and validates the answer against the full response model.
2. Write SPC-02 to SPC-07. Every failure (HTTP error, timeout, refusal, invalid output, empty answer) returns "Flight planner is temporarily unavailable.", "Stay planner is temporarily unavailable.", or "Activity planner is temporarily unavailable.", and logs the cause.
3. Write SPC-09. Every prompt tells the model not to present suggestions as live or bookable.
4. Write SPC-10 and SPC-11. Activities uses the preferences, or "general sightseeing".
5. Replace the phase 3 specialist placeholder with the shared flow.

**BDD.** [BDD] §4.4, "Suggestion generation", every scenario.

**Exit criteria.** `pytest tests` and the BDD command pass.

**Commit.**
```
Generate validated flight, stay, and activity suggestions

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

### Phase 7: Guidance retrieval

**Goal.** Each specialist adds current, English, section-filtered Wikivoyage passages to its prompt, returns their sources, and plans normally without guidance whenever retrieval is unavailable.

**Requirements.** Delivers 080–082, 084–090, 143, 151, 181, 186. Starts 083 (alias resolution; the destination file is finished in phase 8).

**Tests.** CFG-08, then RAG-01 to RAG-23. Parametrize `tests/test_rag.py` over both stores.

**Files.**
- `shared/rag/store.py` (store interface and embedding-identity check)
- `shared/rag/chroma_store.py`, `shared/rag/file_store.py`
- `shared/rag/retriever.py` (aliases, section filters, language and expiry filters, cache, timeout, fallback)
- `shared/rag/guidance.py` (markers, marker stripping, size caps)
- `tests/conftest.py` (`guidance_index` fixture), `tests/test_rag.py`, `tests/test_optional_rag.py`
- `features/rag/guidance_retrieval.feature`, `features/steps/test_guidance_retrieval.py`

**Steps.**
1. Settle the phase 7 decisions in §6 (alias format, cache eviction).
2. Build the `guidance_index` fixture with `FakeEmbedder`, for both stores ([TDD] §2.3).
3. Write CFG-08. The vector store is chosen by configuration.
4. Write RAG-01 to RAG-07. Top-k, sections per agent, language, destination, and expiry filters, aliases, and no embedding call for unknown destinations.
5. Write RAG-08 to RAG-12. Each failure path, including an embedding-identity mismatch, plans without guidance and logs why. Import the Chroma package lazily so that RAG-09 can simulate it being missing.
6. Write RAG-13 to RAG-16. Fence the guidance in `<guidance>` markers, remove copies of the markers from the text, and cap passages at 700 characters and all guidance at 2,400.
7. Write RAG-17 and RAG-18. Sources come only from the passages used.
8. Write RAG-19 to RAG-22. An in-memory cache keyed by agent, destination, and day, with 256 entries.
9. Write RAG-23. Open the stores read-only while serving.
10. Wire the retriever into the phase 6 specialist flow, then run SPC-01 to SPC-11 again.

**BDD.** [BDD] §5.1, "Guidance retrieval", every scenario. The alias scenario writes a temporary destination file in the format settled in step 1.

**Exit criteria.**
- `pytest tests` and the BDD command pass.
- `tests/test_optional_rag.py` passes in an environment without the Chroma package installed.

**Commit.**
```
Ground specialist prompts in retrieved Wikivoyage guidance

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

### Phase 8: Guidance ingest

**Goal.** One command builds and refreshes the guidance index from Wikivoyage, and the cloud index is committed to the repository.

**Requirements.** Delivers 083, 100–107, 152, 171.

**Tests.** ING-01 to ING-14, then REP-03.

**Files.**
- `shared/rag/ingest.py` (command entry point)
- `shared/rag/mediawiki.py` (client with a contact `User-Agent`, 30-day article cache)
- `shared/rag/chunking.py`
- `data/rag/destinations.txt` (20 destinations with aliases)
- the committed cloud index directory †
- `tests/fakes/mediawiki.py`, `tests/test_rag.py` (ingest section)
- `features/ingest/guidance_index.feature`, `features/steps/test_guidance_index.py`

**Steps.**
1. Settle the phase 8 decisions in §6 (passage size tolerance, ingest option names).
2. Build `FakeMediaWiki` ([TDD] §2.3).
3. Write ING-01, ING-02, and ING-10. Read the destinations file, including aliases, or a list given on the command line.
4. Write ING-03 to ING-06. Keep only sections some agent uses, split them into passages of about 300 tokens, store the full metadata, and set validity to one year from download.
5. Write ING-07 to ING-09. Replace passages on re-ingest, cache articles for 30 days, and add the refresh option.
6. Write ING-11 to ING-13. Build the Chroma or file index, refuse a file index with non-OpenAI embeddings, and record the embedding identity.
7. Write ING-14. Every MediaWiki request carries a contact URL in its `User-Agent`.
8. By hand, outside the test suite: run the command against the real MediaWiki API with OpenAI embeddings to build the cloud file index, then commit it. Write REP-03.

**BDD.** [BDD] §5.2, "Guidance index management", every scenario.

**Exit criteria.**
- `pytest tests` and the BDD command pass.
- The cloud index is tracked by git, and RAG-12 passes against it with the cloud embedding settings.

**Commit.**
```
Add the Wikivoyage ingest command and commit the cloud guidance index

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

### Phase 9: Host orchestration

**Goal.** The Host calls the three specialists concurrently and merges their answers into one plan. A failure in one part never hides the others.

**Requirements.** Delivers 003, 005, 060–066, 141, 150, 180.

**Tests.** SRV-08, then HST-01 to HST-10.

**Files.**
- `agents/host/planner.py` (fan-out, response validation, error entries, source merging)
- `tests/fakes/agents.py` (`FakeAgent`)
- `tests/test_host.py`
- `features/api/trip_planning.feature`, `features/api/request_validation.feature`, `features/operations/data_retention.feature`, and their step files

**Steps.**
1. Settle the phase 9 decision in §6 (specialist errors pass through).
2. Build `FakeAgent` ([TDD] §2.3).
3. Write SRV-08 and HST-04. Replace the phase 3 placeholder with a real plan.
4. Write HST-01 to HST-03. Call the specialists with `asyncio.gather`, each under `DOWNSTREAM_TIMEOUT_SECONDS`, sending the normalized request and forwarding `X-Request-ID`.
5. Write HST-05 to HST-07. Validate every response; a transport, status, JSON, validation, or timeout failure becomes "Service is temporarily unavailable." for that part. The status is always 200 for a valid request.
6. Write HST-08. Merge sources, drop malformed ones, and remove duplicates by URL.
7. Write HST-09. The Host imports no model client.
8. Write HST-10. An invalid request reaches no specialist.

**BDD.** [BDD] §4.3, "Trip planning"; §4.2, "Travel request validation"; §6.3, "Data retention"; and the remaining §4.1 scenario, "A request ID is logged and forwarded to every specialist".

**Exit criteria.**
- `pytest tests` and the BDD command pass.
- By hand: with all four agents running locally on Ollama, `POST /run` on the Host returns a full plan.

**Commit.**
```
Plan trips by calling the specialists concurrently and merging results

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

### Phase 10: Metrics

**Goal.** When an OTLP endpoint is configured, every agent pushes request, model, token, and retrieval metrics. Metrics never affect requests.

**Requirements.** Delivers 120, 121, 122.

**Tests.** TEL-01 to TEL-07.

**Files.**
- `shared/telemetry.py`
- `tests/test_telemetry.py`
- `features/metrics/metrics.feature`, `features/steps/test_metrics.py`

**Steps.**
1. Write TEL-01 and TEL-02. Configure an exporter only when `OTEL_EXPORTER_OTLP_ENDPOINT` is set, with an export interval of at most 60 seconds.
2. Write TEL-03 to TEL-06. Record HTTP request metrics in the app factory, model call durations by outcome and token usage by type in the specialist flow, and retrieval durations by outcome in the retriever.
3. Write TEL-07. Export failures are caught and logged.

**BDD.** [BDD] §6.1, "Metrics", every scenario.

**Exit criteria.** `pytest tests` and the BDD command pass.

**Commit.**
```
Export agent metrics over OTLP when an endpoint is configured

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

### Phase 11: Web application

**Goal.** A Next.js single-page app where travelers enter a trip, watch its progress, and read the results. It calls the Host only from server-side code.

**Requirements.** Delivers 010–015, 020–022, 030–033, 040, 041, 043, 130, 132, 142, 160, 170.

**Tests.** WEB-R01 to WEB-R08, then WEB-F01 to WEB-F07, WEB-P01 to WEB-P04, and WEB-T01 to WEB-T05.

**Files.** All under `web/` †.
- `package.json`, `package-lock.json` (exact versions; REP-01 now checks them)
- `app/page.tsx`, `app/api/plan/route.ts` †
- `components/TripForm.tsx`, `components/PlanProgress.tsx`, `components/PlanResults.tsx`
- `tests/unit/plan-route.test.ts`, `tests/unit/TripForm.test.tsx`, `tests/unit/PlanProgress.test.tsx`, `tests/unit/PlanResults.test.tsx`
- `tests/mocks/host.ts` (MSW fake Host)
- `features/web/*.feature` and their playwright-bdd step files

**Steps.**
1. Settle the phase 11 decision in §6 (wording of the unavailable message).
2. Create the Next.js app with pinned versions. Add Vitest, React Testing Library, user-event, and MSW with `onUnhandledRequest: "error"`. Add the web commands to CI.
3. **Server route** (WEB-R01 to WEB-R08). Read `HOST_SERVICE_URL` and `HOST_API_KEY` from server-only environment variables. Send `X-API-Key` only when the key is set. Abort after 180 seconds. Turn every failure into the plain unavailable message.
4. **Form** (WEB-F01 to WEB-F07). Visible labels; travellers 1 to 9, default 1; budget at least 100 in steps of 50; warnings and no request for missing places or bad dates; submit disabled while pending; usable with the keyboard alone.
5. **Progress** (WEB-P01 to WEB-P04). An elapsed-time indicator at the top of the results area, updated every second, that ends as complete, partial, or failed.
6. **Results** (WEB-T01 to WEB-T05). Three tables, one warning per failed part, a collapsed Sources section with links and licenses, and the illustrative-only notice.
7. Add `web/` to the CI workflow and check that REP-01 now covers `package.json`.

**BDD.** Run with playwright-bdd against `next dev`, with the fake Host server from [TDD] §2.3:
- [BDD] §3.1, "Trip form"
- §3.2, "Planning progress"
- §3.3, "Results display", except "Results appear without a full page reload" (phase 12)
- §3.4, "Server-side access to the Host", except the key-exposure outline, which needs a production build (phase 12)

**Exit criteria.**
- `npm test --prefix web` and `npx playwright test` pass, along with all Python suites.
- By hand: the app plans a trip against the local stack from phase 9.

**Commit.**
```
Add the Next.js trip planner with a server-side route to the Host

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

### Phase 12: End-to-end, deployment, and release

**Goal.** The whole system runs self-hosted with Docker Compose and in the cloud on Vercel, passes its end-to-end checks, and is accepted against every requirement.

**Requirements.** Delivers 042, 113, 131, 133, 140, 144, 164, 165, 183, 184, 188.

**Tests.** E2E-01 to E2E-06, then the manual checks in [TDD] §5.

**Files.**
- `web/tests/e2e/*.spec.ts`, `web/tests/e2e/fake-host.ts`
- `Dockerfile` (agents, one image selected by `APP_MODULE`), `web/Dockerfile` (Node.js image)
- `docker-compose.yml`
- `vercel.json` (or the equivalent project configuration)
- `docs/` updates: HTTP API and configuration reference, including which secrets each service receives

**Steps.**
1. **End-to-end** (E2E-01 to E2E-06). Run Playwright against `next build` and `next start`, with the fake Host. E2E-01 searches the built output for a sentinel key, and E2E-04 checks there is no horizontal scrolling from 360 pixels wide.
2. **Self-hosted.** Write `docker-compose.yml` with Ollama, the four agents, and the web container. Do not publish any specialist ports. Keep both Ollama models loaded for at least 30 minutes (for example, `OLLAMA_KEEP_ALIVE=30m` and `OLLAMA_MAX_LOADED_MODELS=2`). Give each service only the secrets it uses.
3. **Cloud.** Configure Vercel so that only the web application and the Host have public routes, the specialists are reached through private service bindings, all public traffic uses HTTPS, and OpenAI is the provider with the committed file index. Pass secrets as Vercel environment variables, per service.
4. **Acceptance.** Run every check in [TDD] §5, and every scenario tagged `@deployment` or `@demonstration` in [BDD]. Record the results, including the warm and cold timings for 140.
5. Update `docs/` and the SDD so they describe the Next.js interface (SRS §1.1).

**BDD.**
- [BDD] §3.5, "Usability"
- §3.3, "Results appear without a full page reload"
- §3.4, the key-exposure outline
- By hand: §4.5, "Only the web application and the Host are public"; §6.2, the cloud timing and self-hosted model scenarios

**Exit criteria.**
- All automated suites pass in CI.
- `docker compose up` plans a trip in the browser with no paid service (188).
- A Vercel preview deployment plans a trip; specialist addresses are not reachable from outside; HTTP is redirected or refused.
- Every row of §5 below is checked off.

**Commit.**
```
Add end-to-end tests and Docker Compose and Vercel deployments

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

## 5. Requirements by phase

Each requirement is listed under the phase that delivers it in full. Some requirements are started earlier, as noted in each phase's "Requirements" line.

| Req | Phase | Req | Phase | Req | Phase | Req | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 001 | 3 | 050 | 2 | 084 | 7 | 130 | 11 |
| 002 | 3 | 051 | 2 | 085 | 7 | 131 | 12 |
| 003 | 9 | 052 | 2 | 086 | 7 | 132 | 11 |
| 004 | 3 | 053 | 2 | 087 | 7 | 133 | 12 |
| 005 | 9 | 060 | 9 | 088 | 7 | 140 | 12 |
| 006 | 3 | 061 | 9 | 089 | 7 | 141 | 9 |
| 010 | 11 | 062 | 9 | 090 | 7 | 142 | 11 |
| 011 | 11 | 063 | 9 | 100 | 8 | 143 | 7 |
| 012 | 11 | 064 | 9 | 101 | 8 | 144 | 12 |
| 013 | 11 | 065 | 9 | 102 | 8 | 150 | 9 |
| 014 | 11 | 066 | 9 | 103 | 8 | 151 | 7 |
| 015 | 11 | 070 | 6 | 104 | 8 | 152 | 8 |
| 020 | 11 | 071 | 5 | 105 | 8 | 160 | 11 |
| 021 | 11 | 072 | 6 | 106 | 8 | 161 | 3 |
| 022 | 11 | 073 | 6 | 107 | 8 | 162 | 2 |
| 030 | 11 | 074 | 2 | 110 | 4 | 163 | 3 |
| 031 | 11 | 075 | 6 | 111 | 4 | 164 | 12 |
| 032 | 11 | 076 | 6 | 112 | 4 | 165 | 12 |
| 033 | 11 | 077 | 5 | 113 | 12 | 166 | 1 |
| 040 | 11 | 080 | 7 | 120 | 10 | 170 | 11 |
| 041 | 11 | 081 | 7 | 121 | 10 | 171 | 8 |
| 042 | 12 | 082 | 7 | 122 | 10 | 172 | 2 |
| 043 | 11 | 083 | 8 | | | 180 | 9 |
| | | | | | | 181 | 7 |
| | | | | | | 182 | 1 |
| | | | | | | 183 | 12 |
| | | | | | | 184 | 12 |
| | | | | | | 185 | 1 |
| | | | | | | 186 | 7 |
| | | | | | | 187 | 1 |
| | | | | | | 188 | 12 |

## 6. Open decisions

These are the assumptions from [TDD] §7. Settle each one before its phase starts. If a decision differs from the assumption, update [TDD] §7 and the affected tests and scenarios at the same time.

| Phase | Decision | Current assumption |
| --- | --- | --- |
| 1 | Web application location | The Next.js app lives in `web/`, and its server route is `app/api/plan/route.ts`. |
| 2 | Shape of an `errors` entry | Each entry names its part (`flights`, `stay`, or `activities`) and has a `message`. |
| 3 | Service names | `/healthz` reports `host`, `flight`, `stay`, and `activities`. |
| 4 | Authentication order | The API key is checked before the request body is validated. |
| 5 | Unknown provider | An unsupported `LLM_PROVIDER` stops startup with a configuration error. |
| 7 | Alias format | Aliases are on the same line as their destination in `data/rag/destinations.txt`; matching is exact. |
| 7 | Cache eviction | When the retrieval cache is full, the least recently used entry is removed. |
| 8 | Passage size | "About 300 tokens" means 200 to 350 tokens, except a section's last passage. |
| 8 | Ingest options | The ingest command has a refresh option and a store option (Chroma or file). |
| 9 | Specialist errors at the Host | A specialist's own `error` message is passed through unchanged. |
| 11 | Unavailable message | "The planning service is unavailable. Please try again later." |

## 7. References

| ID | Document |
| --- | --- |
| [SRS] | `SOFTWARE_REQUIREMENTS_SPECIFICATION.md`, Software Requirements Specification 1.0.0 |
| [TDD] | `TEST_DRIVEN_DEVELOPMENT_PLAN.md`, Test-Driven Development Plan 1.0.0 |
| [BDD] | `BEHAVIOR_DRIVEN_DEVELOPMENT_SCENARIOS.md`, Behavior Scenarios 1.0.0 |
| [SDD] | `SOFTWARE_DESIGN_DOCUMENT.md`, Software Design Document 1.0.0 (not yet in this repository) |
