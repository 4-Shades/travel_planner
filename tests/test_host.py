"""The Host: calling the specialists and merging their answers (TDD plan, iteration 9)."""

import logging
import time

import pytest

from agents.host.app import SERVICE_UNAVAILABLE
from shared.schemas import TripPlan
from tests import factories
from tests.asgi import AppClient
from tests.fakes.agents import AGENT_ENV, FakeAgent
from tests.fakes.llm import OLLAMA_URL, OPENAI_URL

pytestmark = pytest.mark.respx(assert_all_called=False)

PARTS = {"flight": "flights", "stay": "stay", "activities": "activities"}


@pytest.fixture
def agents(respx_mock):
    return {service: FakeAgent(respx_mock, service) for service in PARTS}


@pytest.fixture
def host(agent_app, agents):
    def build(**env):
        return AppClient(agent_app("host", **AGENT_ENV, **env))

    return build


def plan(host, body=None, **env):
    return host(**env).post("/run", json=body or factories.valid_request())


# SRV-08 (TP-SRS-003)
def test_host_run_returns_trip_plan(host):
    response = plan(host)
    assert response.status_code == 200
    TripPlan.model_validate(response.json())


# HST-01 (TP-SRS-060, TP-SRS-141)
def test_specialists_called_concurrently(host, agents):
    for agent in agents.values():
        agent.answer_slowly(0.3)
    client = host()
    start = time.perf_counter()
    response = client.post("/run", json=factories.valid_request())
    elapsed = time.perf_counter() - start
    assert response.status_code == 200
    assert elapsed < 0.5
    assert all(len(agent.requests) == 1 for agent in agents.values())


# HST-02 (TP-SRS-060)
def test_each_specialist_gets_normalized_request(host, agents):
    plan(host, factories.valid_request(origin="San   Francisco", currency="eur"))
    bodies = [agent.requests[0] for agent in agents.values()]
    assert all(body == bodies[0] for body in bodies)
    assert bodies[0]["origin"] == "San Francisco"
    assert bodies[0]["currency"] == "EUR"
    assert bodies[0]["request_id"] and bodies[0]["trip_id"]


# HST-03 (TP-SRS-005)
def test_request_id_forwarded(host, agents):
    host().post("/run", json=factories.valid_request(), headers={"X-Request-ID": "req-123"})
    for agent in agents.values():
        assert agent.headers[0]["X-Request-ID"] == "req-123"


# HST-03: a generated request ID is forwarded too, the same one to every specialist.
def test_generated_request_id_forwarded(host, agents):
    plan(host)
    ids = {agent.headers[0]["X-Request-ID"] for agent in agents.values()}
    assert len(ids) == 1 and ids.pop()


# HST-04 (TP-SRS-062)
def test_complete_plan(host):
    body = plan(host, factories.valid_request(request_id="req-1", trip_id="trip-1")).json()
    assert body["request_id"] == "req-1" and body["trip_id"] == "trip-1"
    assert body["flights"] and body["stay"] and body["activities"]
    assert body["errors"] == []


# HST-05 (TP-SRS-061, TP-SRS-063, TP-SRS-180)
@pytest.mark.parametrize("service", PARTS)
@pytest.mark.parametrize(
    "failure",
    [
        lambda agent: agent.unreachable(),
        lambda agent: agent.fail(500),
        lambda agent: agent.fail(422),
        lambda agent: agent.answer_invalid_json(),
        lambda agent: agent.answer_wrong_model(),
        lambda agent: agent.answer({"unexpected": True}),
        lambda agent: agent.answer(["not", "an", "object"]),
        lambda agent: agent.answer_slowly(2),
    ],
    ids=["unreachable", "500", "422", "invalid-json", "wrong-model", "no-offers", "not-an-object", "too-slow"],
)
def test_failed_agent_recorded_others_returned(host, agents, service, failure):
    failure(agents[service])
    response = plan(host, LLM_TIMEOUT_SECONDS="0.2", DOWNSTREAM_TIMEOUT_SECONDS="0.5")
    assert response.status_code == 200
    body = response.json()
    assert body["errors"] == [{"part": PARTS[service], "message": SERVICE_UNAVAILABLE}]
    assert body[PARTS[service]] == []
    for other, part in PARTS.items():
        if other != service:
            assert body[part], part


# HST-05 (TP-SRS-063, TP-SRS-142): only DOWNSTREAM_TIMEOUT_SECONDS limits the wait, not httpx's 5-second default.
def test_request_uses_downstream_timeout(host, agents):
    plan(host, DOWNSTREAM_TIMEOUT_SECONDS="150")
    for agent in agents.values():
        timeout = agent.route.calls.last.request.extensions["timeout"]
        assert timeout["read"] >= 150 or timeout["read"] is None


# HST-05: the cause of a failure is logged for operators.
def test_failure_cause_logged(host, agents, caplog):
    caplog.set_level(logging.WARNING, logger="travel_planner")
    agents["stay"].fail(503)
    plan(host)
    assert any("stay" in r.getMessage() and "503" in r.getMessage() for r in caplog.records)


# HST-06 (TP-SRS-064)
def test_all_agents_failed_still_200(host, agents):
    for agent in agents.values():
        agent.fail(500)
    response = plan(host)
    assert response.status_code == 200
    body = response.json()
    assert sorted(e["part"] for e in body["errors"]) == ["activities", "flights", "stay"]
    assert body["flights"] == body["stay"] == body["activities"] == []


# HST-07 (TP-SRS-031, TP-SRS-063)
def test_specialist_error_passed_through(host, agents):
    agents["flight"].report_error("Flight planner is temporarily unavailable.")
    body = plan(host).json()
    assert body["errors"] == [{"part": "flights", "message": "Flight planner is temporarily unavailable."}]
    assert body["stay"] and body["activities"]


# HST-08 (TP-SRS-065)
def test_sources_merged_and_deduplicated(host, agents):
    tokyo = factories.source()
    ginza = factories.source(title="Tokyo/Ginza", url="https://en.wikivoyage.org/wiki/Tokyo/Ginza")
    agents["flight"].answer_normally(sources=[tokyo])
    agents["stay"].answer_normally(sources=[tokyo])
    agents["activities"].answer_normally(
        sources=[ginza, {"title": "Broken", "license": "CC BY-SA 4.0"}, {"title": "Bad", "url": "not a url", "license": "x"}]
    )
    body = plan(host).json()
    assert body["sources"] == [tokyo, ginza]
    assert body["errors"] == []


# HST-09 (TP-SRS-066)
def test_host_never_calls_language_model(host, respx_mock, monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("The Host must not create a model client")

    monkeypatch.setattr("shared.llm.create_llm_client", refuse)
    model_routes = [respx_mock.route(url__startswith=url) for url in (OLLAMA_URL, OPENAI_URL, "http://localhost:11434", "https://api.openai.com")]
    assert plan(host).status_code == 200
    assert not any(route.called for route in model_routes)


# HST-09: the Host does not need a model provider's secret (TP-SRS-183).
def test_host_starts_without_openai_key(host):
    assert plan(host, LLM_PROVIDER="openai").status_code == 200


# HST-10 (TP-SRS-004)
def test_invalid_request_calls_no_agent(host, agents):
    response = plan(host, factories.valid_request(travellers=0))
    assert response.status_code == 422
    assert not any(agent.route.called for agent in agents.values())
