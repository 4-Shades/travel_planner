"""The HTTP interface every agent shares (TDD plan, iterations 3 and 4)."""

import hmac
import json
import logging
from pathlib import Path

import pytest

from shared.request_id import LOG_FORMAT
from tests.asgi import AppClient

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ["host", "flight", "stay", "activities"]


@pytest.fixture(params=AGENTS)
def client(request, agent_app):
    return AppClient(agent_app(request.param))


def error_fields(response):
    return {str(part) for error in response.json()["detail"] for part in error["loc"]}


# SRV-01 (TP-SRS-001)
@pytest.mark.parametrize("method, path", [("POST", "/run"), ("GET", "/healthz"), ("GET", "/readyz"), ("GET", "/")])
def test_standard_endpoints_exist(client, method, path):
    response = client.request(method, path, json={} if method == "POST" else None)
    assert response.status_code not in (404, 405)


# SRV-02 (TP-SRS-002)
def test_healthz_reports_service(agent_app):
    for service in AGENTS:
        response = AppClient(agent_app(service)).get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": service}


# SRV-03 (TP-SRS-002)
def test_healthz_needs_no_key(agent_app):
    client = AppClient(agent_app("host", HOST_API_KEY="s3cret"))
    assert client.get("/healthz").status_code == 200


# SRV-04 (TP-SRS-004)
def test_invalid_body_lists_fields(client, valid_request):
    response = client.post("/run", json=valid_request(origin="M", travellers=12))
    assert response.status_code == 422
    assert {"origin", "travellers"} <= error_fields(response)


# SRV-05 (TP-SRS-004)
def test_non_json_body_is_rejected(client):
    response = client.post("/run", content=b"not json", headers={"Content-Type": "application/json"})
    assert response.status_code == 422


# SRV-06 (TP-SRS-005)
def test_request_id_in_logs(client, valid_request, caplog):
    caplog.set_level(logging.INFO, logger="travel_planner")
    client.post("/run", json=valid_request(), headers={"X-Request-ID": "req-123"})
    records = [r for r in caplog.records if r.name.startswith("travel_planner")]
    assert records
    assert all(r.request_id == "req-123" for r in records)
    assert "req-123" in logging.Formatter(LOG_FORMAT).format(records[0])


# SRV-06 (TP-SRS-005): log lines carry a generated ID when the header is absent or unsafe.
@pytest.mark.parametrize("headers", [{}, {"X-Request-ID": "bad id\nforged line"}])
def test_request_id_generated_when_missing_or_unsafe(client, valid_request, caplog, headers):
    caplog.set_level(logging.INFO, logger="travel_planner")
    client.post("/run", json=valid_request(), headers=headers)
    ids = {r.request_id for r in caplog.records if r.name.startswith("travel_planner")}
    assert len(ids) == 1
    assert ids.pop() not in ("-", "bad id\nforged line")


# SRV-06 (TP-SRS-005): uvicorn runs with logging.json, which must print the agent's lines with their ID.
def test_log_config_prints_request_id():
    config = json.loads((ROOT / "logging.json").read_text(encoding="utf-8"))
    handler = config["loggers"]["travel_planner"]["handlers"][0]
    formatter = config["handlers"][handler]["formatter"]
    assert config["formatters"][formatter]["format"] == LOG_FORMAT
    assert config["loggers"]["travel_planner"]["level"] == "INFO"


# SRV-07 (TP-SRS-006)
def test_openapi_schema_served(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "post" in schema["paths"]["/run"]


# Iteration 4: API protection


@pytest.fixture
def keyed_host(agent_app):
    return AppClient(agent_app("host", HOST_API_KEY="s3cret"))


# KEY-01 (TP-SRS-110)
def test_missing_key_rejected(keyed_host, valid_request):
    assert keyed_host.post("/run", json=valid_request()).status_code == 401


# KEY-02 (TP-SRS-110)
@pytest.mark.parametrize("key", ["wrong", "", "s3cret ", "S3CRET", "s3cre"])
def test_wrong_key_rejected(keyed_host, valid_request, key):
    response = keyed_host.post("/run", json=valid_request(), headers={"X-API-Key": key})
    assert response.status_code == 401


# KEY-03 (TP-SRS-110)
def test_matching_key_accepted(keyed_host, valid_request):
    response = keyed_host.post("/run", json=valid_request(), headers={"X-API-Key": "s3cret"})
    assert response.status_code == 200


# KEY-04 (TP-SRS-110)
@pytest.mark.parametrize("body", [{"json": {"origin": "M"}}, {"content": b"not json"}])
def test_key_checked_before_body(keyed_host, body):
    response = keyed_host.post("/run", headers={"Content-Type": "application/json"}, **body)
    assert response.status_code == 401


# KEY-05 (TP-SRS-111)
def test_key_compared_in_constant_time(keyed_host, valid_request, monkeypatch):
    import shared.auth

    calls = []
    real_compare = hmac.compare_digest

    def spy(given, expected):
        calls.append((given, expected))
        return real_compare(given, expected)

    monkeypatch.setattr(shared.auth.hmac, "compare_digest", spy)
    keyed_host.post("/run", json=valid_request(), headers={"X-API-Key": "wrong"})
    assert calls == [(b"wrong", b"s3cret")]


# KEY-06 (TP-SRS-112)
def test_no_key_configured_accepts_requests(agent_app, valid_request):
    assert AppClient(agent_app("host")).post("/run", json=valid_request()).status_code == 200


# KEY-06: an empty HOST_API_KEY counts as not set.
def test_empty_key_counts_as_unset(agent_app, valid_request):
    client = AppClient(agent_app("host", HOST_API_KEY=""))
    assert client.post("/run", json=valid_request()).status_code == 200


# KEY-07 (TP-SRS-132)
def test_401_body_does_not_reveal_key(keyed_host, valid_request):
    response = keyed_host.post("/run", json=valid_request(), headers={"X-API-Key": "wrong"})
    assert "s3cret" not in response.text
    assert response.json() == {"detail": "A valid X-API-Key header is required."}


# Only POST /run is protected: health, readiness, and the schema stay open (TP-SRS-002).
@pytest.mark.parametrize("path", ["/healthz", "/readyz", "/", "/openapi.json"])
def test_other_endpoints_need_no_key(keyed_host, path):
    assert keyed_host.get(path).status_code == 200


# The specialists are not public (TP-SRS-113), so the Host's key does not apply to them.
@pytest.mark.parametrize("service", ["flight", "stay", "activities"])
def test_specialists_do_not_check_host_key(agent_app, valid_request, service):
    client = AppClient(agent_app(service, HOST_API_KEY="s3cret"))
    assert client.post("/run", json=valid_request()).status_code == 200


# The key never appears in a printed settings object.
def test_settings_repr_hides_key(settings):
    assert "s3cret" not in repr(settings(HOST_API_KEY="s3cret"))
