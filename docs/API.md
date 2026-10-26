# HTTP API

The Host is the only agent clients call (SRS §1.3). All messages are JSON over HTTP; dates use `YYYY-MM-DD` and currencies ISO 4217 three-letter codes (TP-SRS-172). The data contracts are defined once, in `shared/schemas.py`.

## Host

| Method and path | Purpose | Key needed |
| --- | --- | --- |
| `POST /run` | Plan a trip | Yes, when `HOST_API_KEY` is set |
| `GET /healthz` | Liveness: `{"status": "ok", "service": "host"}` | No |
| `GET /readyz` | Readiness: `{"status": "ready", "service": "host"}` | No |
| `GET /` | Service name and links | No |
| `GET /openapi.json`, `GET /docs` | OpenAPI schema and its browsable form | No |

### Headers

| Header | Direction | Meaning |
| --- | --- | --- |
| `X-API-Key` | Request | Must match `HOST_API_KEY` when that is set; otherwise status 401 (TP-SRS-110). |
| `X-Request-ID` | Request | Optional. Up to 128 letters, digits, and `._:-`. Used in every log line for the request, by the Host and by each specialist (TP-SRS-005). Any other value is replaced by a generated ID. |

### `POST /run`

Request body:

| Field | Type | Rules |
| --- | --- | --- |
| `origin`, `destination` | string | 2 to 120 characters, after repeated spaces are collapsed |
| `start_date`, `end_date` | date | `YYYY-MM-DD`; `end_date` must be after `start_date` |
| `budget` | number | Greater than 0 |
| `travellers` | integer | 1 to 9 |
| `currency` | string | Optional, three letters, upper-cased; default `USD` |
| `preferences` | list of strings | Optional, at most 20; the Activities agent uses them |
| `user_id` | string | Optional, at most 128 characters; never stored (TP-SRS-150) |
| `request_id`, `trip_id` | string | Optional; generated as UUIDs when absent |

```json
{
  "origin": "Manila",
  "destination": "Tokyo",
  "start_date": "2026-12-01",
  "end_date": "2026-12-06",
  "budget": 1500,
  "travellers": 2,
  "preferences": ["museums"]
}
```

Response, status 200 for every valid request, even when some or all parts failed (TP-SRS-064):

```json
{
  "request_id": "6f1c…",
  "trip_id": "a9b2…",
  "flights": [{"airline": "…", "route": "MNL to HND", "departure_date": "2026-12-01", "return_date": "2026-12-06", "price": 420, "currency": "USD", "notes": "…"}],
  "stay": [{"name": "…", "area": "Shinjuku", "nights": 5, "price": 900, "currency": "USD", "notes": "…"}],
  "activities": [],
  "errors": [{"part": "activities", "message": "Service is temporarily unavailable."}],
  "sources": [{"title": "Tokyo", "url": "https://en.wikivoyage.org/wiki/Tokyo", "license": "CC BY-SA 4.0"}]
}
```

- Each part holds up to three offers. Prices are estimates, zero or more. Suggestions are illustrative, not live or bookable.
- `errors` has one entry for each part that failed. The message is either the Host's "Service is temporarily unavailable." (the specialist could not be reached, failed, answered with something invalid, or took longer than `DOWNSTREAM_TIMEOUT_SECONDS`) or the specialist's own message, such as "Flight planner is temporarily unavailable." (TP-SRS-063).
- `sources` lists the Wikivoyage articles whose text guided the suggestions, once per URL (TP-SRS-065).

Other statuses:

| Status | When | Body |
| --- | --- | --- |
| 401 | `HOST_API_KEY` is set and `X-API-Key` is missing or wrong; checked before the body | `{"detail": "A valid X-API-Key header is required."}` |
| 422 | The body is not JSON, or a field breaks a rule above | FastAPI's `detail` list, one entry per invalid field, with its location (TP-SRS-004) |

## Specialists

The Flight, Stay, and Activities agents have the same `/healthz`, `/readyz`, `/`, and `/openapi.json`, and a `POST /run` that takes the same travel request. They are private: only the Host calls them (TP-SRS-113).

Each answers with its part, its sources, and an `error`, which is set instead of offers when the language model failed (TP-SRS-070, TP-SRS-073):

```json
{"flights": [], "sources": [], "error": "Flight planner is temporarily unavailable."}
```

The part is named `flights`, `stay`, or `activities`, as in the trip plan.

## Web application

| Method and path | Purpose |
| --- | --- |
| `GET /` | The trip planner page |
| `POST /api/plan` | Used by the page. Takes the travel request, calls the Host from the server, and answers `{"plan": …}` (200), or `{"error": "The planning service is unavailable. Please try again later."}` (502) when the Host could not be reached, answered with an error status, or did not answer within `HOST_TIMEOUT_SECONDS`. |
