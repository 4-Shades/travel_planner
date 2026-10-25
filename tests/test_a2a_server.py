"""The HTTP interface every agent shares (TDD plan, iterations 3 and 4)."""

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
