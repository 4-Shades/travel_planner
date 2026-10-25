# Test-Driven Development Plan: ADK-Powered Travel Planner

| Field | Value |
| --- | --- |
| Project | ADK-Powered Travel Planner |
| Document | TDD plan |
| Version | 1.0.0 |
| Date | October 24, 2026 |
| Author | Chaim Joseph Cordova |
| Status | Draft |

**Revision history**

| Name | Date | Reason for changes | Version |
| --- | --- | --- | --- |
| Chaim Joseph Cordova | October 24, 2026 | First version, derived from SRS 1.0.0 | 1.0.0 |

**Contents:** 1. Introduction · 2. Approach · 3. Build order · 4. Test cases · 5. Requirements verified outside the TDD cycle · 6. Traceability · 7. Assumptions to confirm · 8. References

## 1. Introduction

### 1.1 Purpose

This plan turns the SRS into an ordered list of tests to write **before** the code that makes them pass. Every test traces to one or more SRS requirements by ID. The companion document [BDD] describes the same behavior as Gherkin scenarios from the point of view of travelers, API clients, and operators; this plan covers the unit and service tests that drive the design underneath those scenarios.

### 1.2 Scope

The plan covers every requirement whose verification method in SRS §3 is "Test" or "Test and demonstration". It also adds cheap automated checks for some requirements the SRS verifies by inspection. Requirements that can only be verified by demonstration or by inspecting a deployment are listed in §5 with how they are checked.

### 1.3 Conventions

- Requirement IDs are shortened in tables: `050` means **TP-SRS-050**.
- Test IDs have the form `<AREA>-<nn>`, for example `SCH-03`. Areas: `SCH` schemas, `CFG` configuration, `SRV` agent HTTP shell, `KEY` API protection, `LLM` model clients, `SPC` specialists, `RAG` retrieval, `ING` ingest, `HST` Host orchestration, `TEL` metrics, `WEB` web application, `E2E` end-to-end, `REP` repository checks.
- Python test names are pytest function names. Web test names are the `it(...)` description.
- A **fake** is an in-process test double that replaces an external service (see §2.3).
- File paths under `web/` assume the Next.js application lives in a `web/` directory. See §7.

## 2. Approach

### 2.1 The cycle

For each row in §4, in order:

1. **Red.** Write the test. Run it and confirm it fails *for the expected reason*, not because of a typo or a missing import.
2. **Green.** Write the least production code that makes it pass.
3. **Refactor.** Remove duplication and improve names with the whole suite green.
4. **Commit.** Include the test IDs in the commit message, for example `Validate place name length (SCH-02)`.

Rules:

- No production code is written without a failing test that requires it.
- Each test checks one behavior, and its name reads as a sentence.
- Numeric and length limits are tested on both sides of the boundary.
- No test reaches a real external service (TP-SRS-187). Python tests run with `pytest-socket` (`--disable-socket --allow-unix-socket`) so that any real network call fails the test; agents are exercised through `httpx.ASGITransport`, which opens no socket. Web unit tests run MSW with `onUnhandledRequest: "error"`.
- Tests control time with fake clocks (`freezegun` or `time-machine` in Python, `vi.useFakeTimers()` in Vitest). Tests that must measure real concurrency use delays of at most 0.5 seconds.

### 2.2 Test levels and tools

| Level | What it covers | Tools | Location |
| --- | --- | --- | --- |
| Unit (Python) | Schemas, configuration, prompt building, retrieval, ingest steps | pytest | `tests/` |
| Service (Python) | One agent's FastAPI app in process; downstream HTTP faked | pytest, pytest-asyncio, httpx, respx | `tests/` |
| Unit (web) | Components, hooks, and the server route that calls the Host | Vitest, React Testing Library, user-event, MSW | `web/tests/unit/` |
| End-to-end (web) | The built Next.js app in a browser, against a fake Host | Playwright, @axe-core/playwright | `web/tests/e2e/` |
| Behavior | Gherkin scenarios from [BDD] | pytest-bdd, playwright-bdd | `features/` |

### 2.3 Test doubles

| Double | Replaces | Configurable behaviors |
| --- | --- | --- |
| `FakeLLM` (respx routes for Ollama and OpenAI) | Language-model chat endpoints | Valid JSON answer; non-JSON text; JSON that fails the response model; HTTP 500; timeout; OpenAI refusal; token usage counts. Records every request body. |
| `FakeEmbedder` | Embedding endpoints | Deterministic vectors derived from a hash of the text; configurable vector size; raise an error; delay. Counts calls. |
| `FakeAgent` (respx routes on specialist URLs) | Flight, Stay, Activities `POST /run`, for Host tests | Valid answer; delay; HTTP 500; invalid JSON; JSON that fails the response model; connection refused; its own `error` field. Records headers and bodies. |
| `FakeMediaWiki` (respx routes) | MediaWiki `action=query` | Canned article sections with revision IDs. Records `User-Agent` headers and counts calls. |
| `InMemoryMetricReader` (opentelemetry-sdk) | OTLP exporter | Collects metrics in memory for assertions. |
| Fake Host | Host `POST /run`, for web tests | MSW handler in unit tests; a small Node HTTP server in E2E tests. Returns a complete plan, a partial plan, an all-failed plan, HTTP 500, or never answers. Records the `X-API-Key` header. |
| `guidance_index` fixture | Guidance index | A small index built with `FakeEmbedder`, available as both a Chroma store and a file store. Holds passages for Tokyo and New York City in every section, plus a French passage, an expired passage, and passages for another destination. |

### 2.4 Shared fixtures

- `valid_request(**overrides)` returns a valid travel request: origin `Manila`, destination `Tokyo`, start date `2026-12-01`, end date `2026-12-06`, budget `1500`, travellers `2`. Tests change only the field they are about.
- `settings(**env)` sets environment variables with `monkeypatch` and builds a fresh settings object.
- `today` freezes the date at `2026-10-24`.
- `agent_app(name)` builds the FastAPI app for `host`, `flight`, `stay`, or `activities` with fakes attached.
- `caplog` captures log lines.

### 2.5 Continuous integration

pytest, Vitest, and Playwright run in CI on every push and pull request to `main` (SRS §3). Scenarios tagged `@demonstration` or `@deployment` in [BDD] are excluded from CI and run by hand against a deployment.

## 3. Build order

Each iteration depends only on parts tested in earlier iterations: data contracts first, then the agent shell, the specialists, retrieval, the Host, and finally the web application.

| # | Iteration | Requirements | Test files |
| --- | --- | --- | --- |
| 1 | Data contracts | 050–053, 062, 070, 074, 089, 090, 172 | `tests/test_schemas.py` |
| 2 | Configuration | 077, 080, 142, 161, 163, 186 | `tests/test_config.py` |
| 3 | Agent HTTP shell | 001–006 | `tests/test_a2a_server.py` |
| 4 | API protection | 110–112 | `tests/test_a2a_server.py` |
| 5 | Model clients | 071, 073, 077, 120 | `tests/test_ollama_client.py`, `tests/test_openai_client.py` |
| 6 | Specialist planning | 070–076, 132 | `tests/test_specialists.py` |
| 7 | Guidance retrieval | 080–090, 143, 151, 181 | `tests/test_rag.py`, `tests/test_optional_rag.py` |
| 8 | Guidance ingest | 083, 100–107, 171 | `tests/test_rag.py` |
| 9 | Host orchestration | 004, 005, 060–066, 141, 180 | `tests/test_host.py` |
| 10 | Metrics | 120–122 | `tests/test_telemetry.py` |
| 11 | Web server route | 022, 040–043, 132, 142 | `web/tests/unit/plan-route.test.ts` |
| 12 | Web interface | 010–033, 130, 132 | `web/tests/unit/*.test.tsx` |
| 13 | End-to-end and build checks | 021, 031, 032, 040, 042, 130, 131, 133 | `web/tests/e2e/*.spec.ts` |
| 14 | Repository checks | 152, 166, 182 | `tests/test_repository.py` |

## 4. Test cases

### 4.1 Iteration 1: data contracts

File: `tests/test_schemas.py`. All contracts live in `shared/schemas.py` (TP-SRS-162).

| ID | Req | Test | Expectation |
| --- | --- | --- | --- |
| SCH-01 | 050 | `test_valid_request_is_accepted` | `valid_request()` parses without error. |
| SCH-02 | 050 | `test_place_name_length_limits` | For both `origin` and `destination`: 1 character is rejected, 2 and 120 are accepted, 121 is rejected. |
| SCH-03 | 050 | `test_end_date_must_be_after_start_date` | End date equal to start date is rejected; one day earlier is rejected; one day later is accepted. |
| SCH-04 | 050 | `test_budget_must_be_positive` | `0` and `-1` are rejected; `0.01` is accepted. |
| SCH-05 | 050 | `test_travellers_limits` | `0` and `10` are rejected; `1` and `9` are accepted. |
| SCH-06 | 050, 172 | `test_currency_must_be_three_letters` | `"US"`, `"USDD"`, and `"U5D"` are rejected; `"EUR"` and `"eur"` are accepted. |
| SCH-07 | 050 | `test_preferences_limit` | 20 items are accepted; 21 are rejected. |
| SCH-08 | 050 | `test_user_id_length_limit` | Absent is accepted; 128 characters are accepted; 129 are rejected. |
| SCH-09 | 051 | `test_repeated_spaces_are_collapsed` | `"San   Francisco"` becomes `"San Francisco"`, for origin and destination. |
| SCH-10 | 051 | `test_currency_is_upper_cased` | `"eur"` becomes `"EUR"`. |
| SCH-11 | 052 | `test_missing_ids_are_generated` | With `request_id` and `trip_id` absent, each is a valid UUID, and two requests get different values. |
| SCH-12 | 052 | `test_given_ids_are_kept` | Given `request_id` and `trip_id` values are returned unchanged. |
| SCH-13 | 053 | `test_currency_defaults_to_usd` | With `currency` absent, the parsed request has `"USD"`. |
| SCH-14 | 172 | `test_dates_use_iso_8601` | `"2026-12-01"` is accepted; `"01/12/2026"` is rejected; dates serialize as `YYYY-MM-DD`. |
| SCH-15 | 062 | `test_trip_plan_fields` | The trip plan model has exactly `request_id`, `trip_id`, `flights`, `stay`, `activities`, `errors`, and `sources`. |
| SCH-16 | 070 | `test_specialist_response_needs_offers_or_error` | No offers and no error fails validation; one offer passes; an error with no offers passes. Checked for all three specialist response models. |
| SCH-17 | 074 | `test_offer_price_and_currency` | Price `-0.01` is rejected; `0` is accepted; currency `"US"` is rejected. |
| SCH-18 | 089, 170 | `test_source_requires_title_url_license` | A source missing any of `title`, `url`, or `license` fails validation. |
| SCH-19 | 090 | `test_model_schema_has_no_sources_field` | The JSON schema given to the model for each specialist has no `sources` property at any depth. |

### 4.2 Iteration 2: configuration

File: `tests/test_config.py`.

| ID | Req | Test | Expectation |
| --- | --- | --- | --- |
| CFG-01 | 163 | `test_settings_come_from_environment` | Setting an environment variable changes the matching setting; no configuration file is read. |
| CFG-02 | 077, 186 | `test_provider_selects_model_client` | `LLM_PROVIDER=ollama` produces the Ollama client; `LLM_PROVIDER=openai` produces the OpenAI client. |
| CFG-03 | 077 | `test_unknown_provider_fails_at_startup` | `LLM_PROVIDER=other` raises a configuration error naming `LLM_PROVIDER`. |
| CFG-04 | 142 | `test_timeouts_must_nest` | `DOWNSTREAM_TIMEOUT_SECONDS` less than or equal to `LLM_TIMEOUT_SECONDS` raises; 180 or more raises; a value in between is accepted. |
| CFG-05 | 142 | `test_default_timeouts_nest` | The default values satisfy CFG-04. |
| CFG-06 | 080 | `test_rag_top_k_defaults_to_two` | With `RAG_TOP_K` unset, the setting is `2`. |
| CFG-07 | 161 | `test_app_module_selects_agent` | For each of the four `APP_MODULE` values, the built app's `/healthz` reports the matching service name. |
| CFG-08 | 186 | `test_vector_store_selected_by_configuration` | The vector-store setting selects the Chroma store or the file store with no other change. |

### 4.3 Iteration 3: agent HTTP shell

File: `tests/test_a2a_server.py`. Tests marked "all agents" are parametrized over `host`, `flight`, `stay`, and `activities`.

| ID | Req | Test | Expectation |
| --- | --- | --- | --- |
| SRV-01 | 001 | `test_standard_endpoints_exist` (all agents) | `POST /run`, `GET /healthz`, `GET /readyz`, and `GET /` each respond with a status other than 404 or 405. |
| SRV-02 | 002 | `test_healthz_reports_service` (all agents) | `GET /healthz` returns 200 and `{"status": "ok", "service": "<name>"}`. |
| SRV-03 | 002 | `test_healthz_needs_no_key` | With `HOST_API_KEY` set, the Host's `GET /healthz` without a key returns 200. |
| SRV-04 | 004 | `test_invalid_body_lists_fields` (all agents) | A body with an invalid `origin` and an invalid `travellers` returns 422, and the error details name both fields. |
| SRV-05 | 004 | `test_non_json_body_is_rejected` (all agents) | A body that is not JSON returns 422. |
| SRV-06 | 005 | `test_request_id_in_logs` (all agents) | With header `X-Request-ID: req-123`, every log line written while handling the request includes `req-123`. |
| SRV-07 | 006 | `test_openapi_schema_served` (all agents) | `GET /openapi.json` returns 200, with an `openapi` key and a `/run` path. |
| SRV-08 | 003 | `test_host_run_returns_trip_plan` | With all `FakeAgent`s answering, the Host's `POST /run` returns 200 and a body that parses as a trip plan. |

### 4.4 Iteration 4: API protection

File: `tests/test_a2a_server.py`.

| ID | Req | Test | Expectation |
| --- | --- | --- | --- |
| KEY-01 | 110 | `test_missing_key_rejected` | `HOST_API_KEY=s3cret`, no `X-API-Key` header: 401. |
| KEY-02 | 110 | `test_wrong_key_rejected` | `HOST_API_KEY=s3cret`, header `wrong`: 401. |
| KEY-03 | 110 | `test_matching_key_accepted` | `HOST_API_KEY=s3cret`, header `s3cret`: 200. |
| KEY-04 | 110 | `test_key_checked_before_body` | Key set, no header, and an invalid body: 401, not 422. |
| KEY-05 | 111 | `test_key_compared_in_constant_time` | A spy on `hmac.compare_digest` (or `secrets.compare_digest`) is called with the given and expected keys. |
| KEY-06 | 112 | `test_no_key_configured_accepts_requests` | `HOST_API_KEY` unset, no header: 200. |
| KEY-07 | 132 | `test_401_body_does_not_reveal_key` | The 401 response body does not contain the configured key. |

### 4.5 Iteration 5: model clients

Files: `tests/test_ollama_client.py`, `tests/test_openai_client.py`. Rows marked "both" are written once per file.

| ID | Req | Test | Expectation |
| --- | --- | --- | --- |
| LLM-01 | 071 | `test_ollama_requests_schema_json_at_temperature_zero` | The `POST /api/chat` body has `format` equal to the given JSON schema, `options.temperature` equal to `0`, and `stream` equal to `false`. |
| LLM-02 | 071 | `test_openai_requests_strict_schema_at_temperature_zero` | The chat completions body has `response_format.type` equal to `json_schema`, `strict: true`, the given schema, and `temperature: 0`. |
| LLM-03 | 073 | `test_http_error_raises_llm_error` (both) | An HTTP 500 raises the client's error type. |
| LLM-04 | 073 | `test_timeout_raises_llm_error` (both) | The HTTP client is built with `LLM_TIMEOUT_SECONDS`, and a read timeout raises the client's error type. |
| LLM-05 | 073 | `test_refusal_raises_llm_error` | An OpenAI answer with `refusal` set raises the client's error type. |
| LLM-06 | 072, 073 | `test_non_json_answer_raises` (both) | Answer content that is not JSON raises the client's error type. |
| LLM-07 | 120 | `test_token_usage_reported` (both) | The client returns prompt and completion token counts: Ollama `prompt_eval_count` and `eval_count`; OpenAI `usage.prompt_tokens` and `usage.completion_tokens`. |
| LLM-08 | 085, 086 | `test_embeddings_have_configured_size` (both) | Embedding calls return vectors of the configured size; a vector of a different size raises. |

### 4.6 Iteration 6: specialist planning

File: `tests/test_specialists.py`. Parametrized over the three specialists, with `FakeLLM` and retrieval disabled.

| ID | Req | Test | Expectation |
| --- | --- | --- | --- |
| SPC-01 | 070, 072 | `test_valid_answer_returns_offers` | A valid model answer gives 200 and at least one validated offer. |
| SPC-02 | 073 | `test_model_error_returns_planner_unavailable` | A model HTTP error gives `error` equal to `"Flight planner is temporarily unavailable."`, `"Stay planner is temporarily unavailable."`, or `"Activity planner is temporarily unavailable."`. |
| SPC-03 | 073 | `test_model_timeout_returns_planner_unavailable` | A model timeout gives the same message. |
| SPC-04 | 073 | `test_model_refusal_returns_planner_unavailable` | An OpenAI refusal gives the same message. |
| SPC-05 | 072, 073, 074 | `test_invalid_answer_returns_planner_unavailable` | A model answer with a negative price gives the same message. |
| SPC-06 | 070, 073 | `test_empty_answer_returns_planner_unavailable` | A model answer with no offers and no error gives the same message. |
| SPC-07 | 073, 132 | `test_cause_logged_not_returned` | After a model failure, the log contains the exception type; the response body contains no provider name, stack trace, or key. |
| SPC-08 | 071 | `test_agent_response_schema_sent_to_model` | The schema in the model request equals the agent's response schema from `shared/schemas.py`. |
| SPC-09 | 075 | `test_prompt_says_not_live_or_bookable` | The prompt sent to the model tells it not to present suggestions as live or bookable. |
| SPC-10 | 076 | `test_activities_prompt_uses_preferences` | With preferences `["museums", "street food"]`, the Activities prompt includes both. |
| SPC-11 | 076 | `test_activities_prompt_defaults_to_general_sightseeing` | With no preferences, the Activities prompt includes `"general sightseeing"`. |

### 4.7 Iteration 7: guidance retrieval

Files: `tests/test_rag.py` (parametrized over the Chroma store and the file store) and `tests/test_optional_rag.py` (behavior when optional packages or the index are missing). Uses `guidance_index`, `FakeEmbedder`, and `FakeLLM`.

| ID | Req | Test | Expectation |
| --- | --- | --- | --- |
| RAG-01 | 080 | `test_adds_up_to_top_k_passages` | For Tokyo, the prompt has at most 2 passages by default and at most 3 with `RAG_TOP_K=3`. |
| RAG-02 | 081 | `test_agent_reads_only_its_sections` | Every passage used by Flight is from Get in or Get around; by Stay, from Sleep, Stay safe, or Understand; by Activities, from See, Do, Eat, or Drink. |
| RAG-03 | 082 | `test_non_english_passages_excluded` | The French Tokyo passage is never returned. |
| RAG-04 | 082 | `test_other_destinations_excluded` | A Tokyo request never returns another destination's passages. |
| RAG-05 | 082 | `test_expired_passages_excluded` | A passage whose validity ended yesterday is excluded; one valid through today is included. |
| RAG-06 | 083 | `test_alias_resolves_to_destination` | Destination `"NYC"` returns New York City passages. |
| RAG-07 | 084 | `test_unknown_destination_skips_embedding` | For `"Atlantis"`, `FakeEmbedder` is called 0 times and the prompt has no guidance. |
| RAG-08 | 085, 181 | `test_missing_index_plans_without_guidance` | With no index on disk, the response has offers, no error, and no sources, and the reason is logged. |
| RAG-09 | 085, 181 | `test_missing_package_plans_without_guidance` | With the vector-store import patched to raise `ImportError`, same as RAG-08. |
| RAG-10 | 085, 181 | `test_embedding_failure_plans_without_guidance` | With `FakeEmbedder` raising, same as RAG-08. |
| RAG-11 | 085, 181 | `test_slow_lookup_plans_without_guidance` | With a lookup slower than `RAG_TIMEOUT_SECONDS`, same as RAG-08, and the request is not held for the whole lookup. |
| RAG-12 | 086 | `test_identity_mismatch_disables_retrieval` | An index built with a different provider, model, or vector size disables retrieval at startup; the warning names both identities; no embedding call is made. |
| RAG-13 | 087 | `test_guidance_is_fenced` | The prompt has guidance inside `<guidance>` and `</guidance>`, with an instruction to treat it as reference only. |
| RAG-14 | 087 | `test_marker_copies_removed` | A passage containing `<guidance>` and `</guidance>` has them removed, leaving exactly one pair of markers in the prompt. |
| RAG-15 | 088 | `test_passage_length_capped` | A 1,000-character passage appears in the prompt as at most 700 characters. |
| RAG-16 | 088 | `test_total_guidance_capped` | With `RAG_TOP_K=5` and 700-character passages, all guidance together is at most 2,400 characters. |
| RAG-17 | 089 | `test_sources_of_used_passages_returned` | The response sources are exactly the sources of the passages in the prompt, each with title, URL, and license. |
| RAG-18 | 090 | `test_model_cannot_add_sources` | A model answer with an extra `sources` field does not change the response sources. |
| RAG-19 | 143 | `test_cache_hit_same_day` | Two identical lookups on the same day make one embedding call. |
| RAG-20 | 143 | `test_cache_miss_next_day` | After the clock moves to the next day, the lookup makes a new embedding call. |
| RAG-21 | 143 | `test_cache_keyed_by_agent` | Flight and Stay lookups for the same destination and day are cached separately. |
| RAG-22 | 143 | `test_cache_holds_256_entries` | After 257 distinct keys, the cache holds 256 entries. |
| RAG-23 | 151 | `test_serving_does_not_change_index` | After serving requests, the file store's file hashes and the Chroma collection's count are unchanged. |

### 4.8 Iteration 8: guidance ingest

File: `tests/test_rag.py`, ingest section. Uses `FakeMediaWiki`, `FakeEmbedder`, a temporary destinations file, and a frozen clock.

| ID | Req | Test | Expectation |
| --- | --- | --- | --- |
| ING-01 | 100 | `test_ingests_destinations_file` | With a destinations file listing Tokyo and Kyoto, both are fetched and stored. |
| ING-02 | 083, 100 | `test_aliases_loaded_from_destinations_file` | An alias listed in the file (for example `NYC` for New York City) is stored for lookup. |
| ING-03 | 101 | `test_unused_sections_dropped` | Sections no agent uses, such as History, are not stored. |
| ING-04 | 101 | `test_passages_about_300_tokens` | Every passage is within the agreed tolerance of 300 tokens (see §7). |
| ING-05 | 101 | `test_passage_metadata_complete` | Every stored passage has destination, section, title, source URL, revision ID, license, language, and validity dates. |
| ING-06 | 102 | `test_passages_expire_after_one_year` | Downloaded on 2026-10-24, a passage is valid until 2027-10-24. |
| ING-07 | 103 | `test_reingest_replaces_passages` | Ingesting Tokyo twice leaves the same passage count, with the new revision ID. |
| ING-08 | 104 | `test_cache_used_within_30_days` | A second run 29 days later makes no MediaWiki call; a run 31 days later does. |
| ING-09 | 104 | `test_refresh_option_downloads_again` | With the refresh option, MediaWiki is called despite a fresh cache. |
| ING-10 | 105 | `test_destination_list_overrides_file` | Given the list `["Tokyo"]`, only Tokyo is fetched. |
| ING-11 | 106 | `test_builds_chroma_or_file_index` | The Chroma option builds a Chroma index; the file option builds a file index. |
| ING-12 | 106 | `test_cloud_index_refuses_non_openai_embeddings` | The file option with Ollama embeddings exits with a non-zero code and a message, and writes nothing. |
| ING-13 | 107 | `test_index_records_embedding_identity` | Both index types record provider, model, and vector size. |
| ING-14 | 171 | `test_mediawiki_user_agent_has_contact_url` | Every MediaWiki request has a `User-Agent` header containing a contact URL. |

### 4.9 Iteration 9: Host orchestration

File: `tests/test_host.py`. Uses `FakeAgent` for each specialist.

| ID | Req | Test | Expectation |
| --- | --- | --- | --- |
| HST-01 | 060, 141 | `test_specialists_called_concurrently` | With each agent taking 0.3 seconds, the Host answers in under 0.5 seconds. |
| HST-02 | 060 | `test_each_specialist_gets_normalized_request` | Each agent receives the same request, with normalized fields and generated IDs. |
| HST-03 | 005 | `test_request_id_forwarded` | `X-Request-ID: req-123` reaches all three agents. |
| HST-04 | 062 | `test_complete_plan` | With all agents answering, the plan has every field, offers in each part, and an empty `errors`. |
| HST-05 | 061, 063, 180 | `test_failed_agent_recorded_others_returned` | Parametrized over unreachable, HTTP 500, invalid JSON, JSON failing the response model, and slower than `DOWNSTREAM_TIMEOUT_SECONDS`: `errors` has one entry for that part with `"Service is temporarily unavailable."`, and the other two parts have offers. |
| HST-06 | 064 | `test_all_agents_failed_still_200` | With all three failing, the status is 200, `errors` has three entries, and no part has offers. |
| HST-07 | 031, 063 | `test_specialist_error_passed_through` | An agent answering with its own `error` produces an `errors` entry for that part with that message (see §7). |
| HST-08 | 065 | `test_sources_merged_and_deduplicated` | Sources from all agents are merged; a URL returned by two agents appears once; a source without a URL is dropped. |
| HST-09 | 066 | `test_host_never_calls_language_model` | With the model client constructors patched to raise and respx routes on Ollama and OpenAI, a plan succeeds and no model route is called. |
| HST-10 | 004 | `test_invalid_request_calls_no_agent` | An invalid request returns 422, and no `FakeAgent` is called. |

### 4.10 Iteration 10: metrics

File: `tests/test_telemetry.py`. Uses `InMemoryMetricReader`.

| ID | Req | Test | Expectation |
| --- | --- | --- | --- |
| TEL-01 | 121 | `test_no_endpoint_no_metrics` | With `OTEL_EXPORTER_OTLP_ENDPOINT` unset, no OTLP exporter is configured and no OTLP request is made. |
| TEL-02 | 120 | `test_export_interval_at_most_one_minute` | With the endpoint set, the periodic reader's interval is at most 60 seconds. |
| TEL-03 | 120 | `test_http_request_metrics` | One request records an HTTP request metric with route and status. |
| TEL-04 | 120 | `test_model_call_duration_by_outcome` | Model call durations are recorded with outcomes for success, error, and timeout. |
| TEL-05 | 120 | `test_token_usage_by_type` | Token usage is recorded with types for prompt and completion tokens. |
| TEL-06 | 120 | `test_retrieval_duration_by_outcome` | Retrieval durations are recorded with an outcome label for each path in RAG-07 to RAG-11. |
| TEL-07 | 122 | `test_export_failure_does_not_affect_requests` | With the exporter raising on export, requests still return 200 and the failure is logged. |

### 4.11 Iteration 11: web server route

File: `web/tests/unit/plan-route.test.ts`. Tests the server-side route that forwards trip requests to the Host, with the Host faked by MSW.

| ID | Req | Test | Expectation |
| --- | --- | --- | --- |
| WEB-R01 | 040, 041 | `forwards the trip to HOST_SERVICE_URL/run` | The route posts the trip to `${HOST_SERVICE_URL}/run` and returns the plan. |
| WEB-R02 | 043 | `sends X-API-Key when HOST_API_KEY is set` | The Host receives `X-API-Key` equal to `HOST_API_KEY`. |
| WEB-R03 | 043 | `sends no X-API-Key when HOST_API_KEY is unset` | The Host receives no `X-API-Key` header. |
| WEB-R04 | 042 | `never returns the key` | For Host answers of 200, 401, and 500, the route's response body and headers do not contain the key. |
| WEB-R05 | 022 | `reports unavailable on Host error status` | A Host 500 makes the route return the "planning service is unavailable" result. |
| WEB-R06 | 022 | `reports unavailable when Host unreachable` | A network error gives the same result. |
| WEB-R07 | 022, 142 | `gives up after 180 seconds` | With fake timers and a Host that never answers, the request is aborted at 180 seconds and gives the same result. |
| WEB-R08 | 132 | `error messages are plain` | The messages in WEB-R05 to WEB-R07 contain no provider name, stack trace, URL, or key. |

### 4.12 Iteration 12: web interface

Files: `web/tests/unit/TripForm.test.tsx`, `PlanProgress.test.tsx`, `PlanResults.test.tsx`. The call to the server route is mocked.

| ID | Req | Test | Expectation |
| --- | --- | --- | --- |
| WEB-F01 | 010, 130 | `shows every field with a visible label` | `getByLabelText` finds origin, destination, start date, end date, budget in USD, and travellers. |
| WEB-F02 | 011 | `travellers accepts 1 to 9 and defaults to 1` | The field shows 1; 1 and 9 are valid; 0, 10, and 2.5 are invalid and block submission. |
| WEB-F03 | 012 | `budget accepts 100 or more in steps of 50` | 100 and 150 are valid; 99 and 125 are invalid and block submission. |
| WEB-F04 | 013 | `empty origin or destination warns and does not send` | With either field empty, a warning appears and the route is not called. |
| WEB-F05 | 014 | `end date not after start date warns and does not send` | With the end date equal to or before the start date, a warning appears and the route is not called. |
| WEB-F06 | 015 | `disables submit while planning` | Submit is disabled while the request is pending and enabled after it settles. |
| WEB-F07 | 130 | `can be completed with the keyboard alone` | Using only Tab, typing, and Enter, user-event fills and submits the form. |
| WEB-P01 | 020 | `shows elapsed time while planning` | While pending, the indicator is the first element of the results area and shows 0 seconds; after advancing fake timers 3 seconds, it shows 3 seconds. |
| WEB-P02 | 021 | `marks complete when no part failed` | A plan with empty `errors` sets the indicator to complete. |
| WEB-P03 | 021 | `marks partial when a part failed` | A plan with one error sets the indicator to partial. |
| WEB-P04 | 022 | `marks failed when the service is unavailable` | An unavailable result sets the indicator to failed and shows the unavailable message. |
| WEB-T01 | 030 | `shows three result tables` | Tables named Flights, Accommodation, and Activities each have one row per offer. |
| WEB-T02 | 031 | `shows a warning per failed part` | Each `errors` entry produces a warning naming the part and its message. |
| WEB-T03 | 032, 170 | `lists sources collapsed with links and licenses` | The Sources section is collapsed by default; each title is a link to its URL; each license is shown. |
| WEB-T04 | 032 | `hides sources when there are none` | A plan with no sources shows no Sources section. |
| WEB-T05 | 033 | `states suggestions are illustrative` | The page states that suggestions are illustrative and not live or bookable. |

### 4.13 Iteration 13: end-to-end and build checks

Files: `web/tests/e2e/*.spec.ts`. Playwright runs against `next build` and `next start`, with `HOST_SERVICE_URL` pointing at the fake Host server.

| ID | Req | Test | Expectation |
| --- | --- | --- | --- |
| E2E-01 | 042 | `key never reaches the browser` | Built with `HOST_API_KEY` set to a sentinel value, the sentinel appears in no rendered HTML, no file under `.next/static`, and no response the browser receives. |
| E2E-02 | 040 | `browser never calls the Host` | During a plan, no browser request goes to the Host's origin. |
| E2E-03 | 130 | `form is accessible and keyboard operable` | axe reports no label violations, and a keyboard-only flow reaches the results. |
| E2E-04 | 131 | `no horizontal scrolling from 360 pixels` | At widths 360 and 1280, `scrollWidth` is at most `clientWidth`, before and after results render. |
| E2E-05 | 133 | `results appear without a full reload` | A marker set on `window` before submitting is still present when results appear. |
| E2E-06 | 021, 031, 032 | `partial plan end to end` | A partial plan from the fake Host shows the partial indicator, the warning, and the sources. |

### 4.14 Iteration 14: repository checks

File: `tests/test_repository.py`.

| ID | Req | Test | Expectation |
| --- | --- | --- | --- |
| REP-01 | 166 | `test_dependencies_pinned` | Every Python requirement uses `==`; no `package.json` dependency uses `^`, `~`, `*`, or a range; a lockfile is committed. |
| REP-02 | 182 | `test_secrets_ignored` | `.gitignore`, `.dockerignore`, and `.vercelignore` each exclude `.env` files and Terraform state. |
| REP-03 | 152 | `test_cloud_index_committed` | The cloud index files exist at their configured path and are tracked by git. |

A secret scanner such as gitleaks should also run in CI to support TP-SRS-182.

## 5. Requirements verified outside the TDD cycle

| Req | Method | How it is checked |
| --- | --- | --- |
| 113, 165 | Inspection and demonstration | The Vercel configuration gives public routes only to the web application and the Host; requests from outside to specialist addresses fail. Docker Compose publishes no specialist ports. |
| 140 | Demonstration | Timed requests against a preview deployment: warm at most 10 seconds, cold at most 30 seconds. |
| 144 | Demonstration | Docker Compose sets Ollama to keep two models loaded for at least 30 minutes; `ollama ps` shows both models loaded. |
| 150 | Inspection | Code review confirms there is no database and no file write in the request path. |
| 160, 161, 162, 164 | Inspection | Project structure, `APP_MODULE` handling, a single `shared/schemas.py`, Docker Compose and Vercel configuration. CFG-07 also covers 161. |
| 183 | Inspection | Each service's environment in Docker Compose and Vercel lists only the secrets it uses. |
| 184 | Demonstration | Plain HTTP requests to the cloud deployment are redirected or refused. |
| 185 | Inspection | CI workflows use OpenID Connect federation and store no long-lived cloud keys. |
| 187 | Test | The socket guard in §2.1 makes the whole suite fail on any external call. |
| 188 | Inspection | The self-hosted stack uses no paid service; cloud billing shows no idle charge beyond model usage. |

## 6. Traceability

Every SRS requirement and the tests that verify it. "§5" means it is checked outside the TDD cycle.

| Req | Tests |
| --- | --- |
| 001 | SRV-01 |
| 002 | SRV-02, SRV-03 |
| 003 | SRV-08 |
| 004 | SRV-04, SRV-05, HST-10 |
| 005 | SRV-06, HST-03 |
| 006 | SRV-07 |
| 010 | WEB-F01 |
| 011 | WEB-F02 |
| 012 | WEB-F03 |
| 013 | WEB-F04 |
| 014 | WEB-F05 |
| 015 | WEB-F06 |
| 020 | WEB-P01 |
| 021 | WEB-P02, WEB-P03, E2E-06 |
| 022 | WEB-R05, WEB-R06, WEB-R07, WEB-P04 |
| 030 | WEB-T01 |
| 031 | WEB-T02, HST-07, E2E-06 |
| 032 | WEB-T03, WEB-T04, E2E-06 |
| 033 | WEB-T05 |
| 040 | WEB-R01, E2E-02 |
| 041 | WEB-R01 |
| 042 | WEB-R04, E2E-01 |
| 043 | WEB-R02, WEB-R03 |
| 050 | SCH-01 to SCH-08 |
| 051 | SCH-09, SCH-10 |
| 052 | SCH-11, SCH-12 |
| 053 | SCH-13 |
| 060 | HST-01, HST-02 |
| 061 | HST-05 |
| 062 | SCH-15, HST-04 |
| 063 | HST-05, HST-07 |
| 064 | HST-06 |
| 065 | HST-08 |
| 066 | HST-09 |
| 070 | SCH-16, SPC-01, SPC-06 |
| 071 | LLM-01, LLM-02, SPC-08 |
| 072 | LLM-06, SPC-01, SPC-05 |
| 073 | LLM-03 to LLM-06, SPC-02 to SPC-07 |
| 074 | SCH-17, SPC-05 |
| 075 | SPC-09 |
| 076 | SPC-10, SPC-11 |
| 077 | CFG-02, CFG-03 |
| 080 | CFG-06, RAG-01 |
| 081 | RAG-02 |
| 082 | RAG-03, RAG-04, RAG-05 |
| 083 | RAG-06, ING-02 |
| 084 | RAG-07 |
| 085 | LLM-08, RAG-08 to RAG-11 |
| 086 | LLM-08, RAG-12 |
| 087 | RAG-13, RAG-14 |
| 088 | RAG-15, RAG-16 |
| 089 | SCH-18, RAG-17 |
| 090 | SCH-19, RAG-18 |
| 100 | ING-01, ING-02 |
| 101 | ING-03, ING-04, ING-05 |
| 102 | ING-06 |
| 103 | ING-07 |
| 104 | ING-08, ING-09 |
| 105 | ING-10 |
| 106 | ING-11, ING-12 |
| 107 | ING-13 |
| 110 | KEY-01 to KEY-04 |
| 111 | KEY-05 |
| 112 | KEY-06 |
| 113 | §5 |
| 120 | LLM-07, TEL-02 to TEL-06 |
| 121 | TEL-01 |
| 122 | TEL-07 |
| 130 | WEB-F01, WEB-F07, E2E-03 |
| 131 | E2E-04 |
| 132 | KEY-07, SPC-07, WEB-R08 |
| 133 | E2E-05 |
| 140 | §5 |
| 141 | HST-01 |
| 142 | CFG-04, CFG-05, WEB-R07 |
| 143 | RAG-19 to RAG-22 |
| 144 | §5 |
| 150 | §5 |
| 151 | RAG-23 |
| 152 | REP-03 |
| 160 | §5 |
| 161 | CFG-07, §5 |
| 162 | §5 |
| 163 | CFG-01 |
| 164 | §5 |
| 165 | §5 |
| 166 | REP-01 |
| 170 | SCH-18, WEB-T03 |
| 171 | ING-14 |
| 172 | SCH-06, SCH-14 |
| 180 | HST-05 |
| 181 | RAG-08 to RAG-11 |
| 182 | REP-02 |
| 183 | §5 |
| 184 | §5 |
| 185 | §5 |
| 186 | CFG-02, CFG-08 |
| 187 | §2.1 socket guard, §5 |
| 188 | §5 |

## 7. Assumptions to confirm

The SRS leaves these details open. The tests above assume the values shown; confirm or change them before writing the matching tests.

| Topic | Assumption | Affects |
| --- | --- | --- |
| Web application location | The Next.js app lives in `web/`, and its server route is `app/api/plan/route.ts`. | §4.11 to §4.13 |
| Service names | `/healthz` reports `host`, `flight`, `stay`, and `activities`. | SRV-02, CFG-07 |
| Shape of an `errors` entry | Each entry names its part (`flights`, `stay`, or `activities`) and has a `message`. | HST-05 to HST-07, WEB-T02 |
| Specialist errors at the Host | When a specialist answers with its own `error`, the Host passes that message through, rather than replacing it with "Service is temporarily unavailable." | HST-07 |
| Unknown provider | An unsupported `LLM_PROVIDER` stops startup with a configuration error. | CFG-03 |
| Authentication order | The API key is checked before the request body is validated. | KEY-04 |
| Passage size | "About 300 tokens" means between 200 and 350 tokens with the ingest tokenizer, except for a section's last passage, which may be shorter. | ING-04 |
| Alias format | `data/rag/destinations.txt` lists aliases on the same line as the destination, in a format to be defined. Alias matching is exact, as the SRS says. | ING-02, RAG-06 |
| Ingest options | The ingest command has a refresh option and a store option (Chroma or file); names to be defined. | ING-09, ING-11 |
| Unavailable message | The web application shows "The planning service is unavailable. Please try again later." | WEB-R05 to WEB-R08, WEB-P04 |
| Cache eviction | When the retrieval cache is full, the least recently used entry is removed. | RAG-22 |

## 8. References

| ID | Document |
| --- | --- |
| [SRS] | `SOFTWARE_REQUIREMENTS_SPECIFICATION.md`, Software Requirements Specification 1.0.0 |
| [BDD] | `BEHAVIOR_DRIVEN_DEVELOPMENT_SCENARIOS.md`, Gherkin behavior scenarios 1.0.0 |
| [SDD] | `SOFTWARE_DESIGN_DOCUMENT.md`, Software Design Document 1.0.0 |
