"""The Flight, Stay, and Activities agents' planning (TDD plan, iteration 6)."""

import logging

import pytest

from agents.specialist import NOT_LIVE_OR_BOOKABLE, UNAVAILABLE
from shared.schemas import SPECIALISTS
from tests import factories
from tests.asgi import AppClient
from tests.fakes.llm import OPENAI_KEY, PROVIDER_ENV, FakeLLM

SERVICES = list(SPECIALISTS)


@pytest.fixture
def plan(agent_app, valid_request):
    """Post a travel request to a specialist and return its response."""

    def post(service, provider="ollama", **request_fields):
        app = agent_app(service, **PROVIDER_ENV[provider], RAG_ENABLED="false")
        return AppClient(app).post("/run", json=valid_request(**request_fields))

    return post


@pytest.fixture
def llm(respx_mock):
    return FakeLLM(respx_mock, "ollama")


def answer_with(service, **overrides):
    return {SPECIALISTS[service].part: [factories.OFFERS[service](**overrides)]}


# SPC-01 (TP-SRS-070, TP-SRS-072)
@pytest.mark.parametrize("service", SERVICES)
def test_valid_answer_returns_offers(plan, llm, service):
    llm.answer(answer_with(service))
    response = plan(service)
    assert response.status_code == 200
    body = SPECIALISTS[service].response.model_validate(response.json())
    assert len(body.offers()) == 1
    assert body.error is None


# SPC-01: two or three suggestions each (SRS §1.2); extra ones are dropped.
@pytest.mark.parametrize("service", SERVICES)
def test_at_most_three_offers(plan, llm, service):
    llm.answer({SPECIALISTS[service].part: [factories.OFFERS[service]() for _ in range(5)]})
    assert len(plan(service).json()[SPECIALISTS[service].part]) == 3


def assert_planner_unavailable(response, service):
    assert response.status_code == 200
    body = response.json()
    assert body["error"] == UNAVAILABLE[service]
    assert body[SPECIALISTS[service].part] == []


# SPC-02 (TP-SRS-073)
@pytest.mark.parametrize("service", SERVICES)
@pytest.mark.parametrize("status", [500, 503])
def test_model_error_returns_planner_unavailable(plan, llm, service, status):
    llm.fail(status)
    assert_planner_unavailable(plan(service), service)


def test_unavailable_messages():
    assert UNAVAILABLE == {
        "flight": "Flight planner is temporarily unavailable.",
        "stay": "Stay planner is temporarily unavailable.",
        "activities": "Activity planner is temporarily unavailable.",
    }


# SPC-03 (TP-SRS-073)
@pytest.mark.parametrize("service", SERVICES)
def test_model_timeout_returns_planner_unavailable(plan, llm, service):
    llm.time_out()
    assert_planner_unavailable(plan(service), service)


# SPC-04 (TP-SRS-073)
@pytest.mark.parametrize("service", SERVICES)
def test_model_refusal_returns_planner_unavailable(plan, respx_mock, service):
    FakeLLM(respx_mock, "openai").refuse()
    assert_planner_unavailable(plan(service, provider="openai"), service)


# SPC-05 (TP-SRS-072, TP-SRS-073, TP-SRS-074)
@pytest.mark.parametrize("service", SERVICES)
@pytest.mark.parametrize("overrides", [{"price": -10}, {"currency": "US"}, {"price": "cheap"}])
def test_invalid_answer_returns_planner_unavailable(plan, llm, service, overrides):
    llm.answer(answer_with(service, **overrides))
    assert_planner_unavailable(plan(service), service)


# SPC-05: an answer that is not the expected JSON at all.
@pytest.mark.parametrize("service", SERVICES)
@pytest.mark.parametrize("content", [{}, {"offers": []}, {"flights": "none", "stay": "none", "activities": "none"}])
def test_wrong_shape_returns_planner_unavailable(plan, llm, service, content):
    llm.answer(content)
    assert_planner_unavailable(plan(service), service)


# SPC-06 (TP-SRS-070, TP-SRS-073)
@pytest.mark.parametrize("service", SERVICES)
def test_empty_answer_returns_planner_unavailable(plan, llm, service):
    llm.answer({SPECIALISTS[service].part: []})
    assert_planner_unavailable(plan(service), service)


# SPC-07 (TP-SRS-073, TP-SRS-132)
@pytest.mark.parametrize("service", SERVICES)
@pytest.mark.parametrize("provider", ["ollama", "openai"])
def test_cause_logged_not_returned(plan, respx_mock, caplog, service, provider):
    FakeLLM(respx_mock, provider).fail(401)
    caplog.set_level(logging.WARNING, logger="travel_planner")
    response = plan(service, provider=provider)
    assert any("LLMError" in record.getMessage() for record in caplog.records)
    for secret in ("Ollama", "OpenAI", "ollama", "openai", "Traceback", OPENAI_KEY, "HTTP 401"):
        assert secret not in response.text


# SPC-08 (TP-SRS-071)
@pytest.mark.parametrize("service", SERVICES)
def test_agent_response_schema_sent_to_model(plan, llm, service):
    llm.answer(answer_with(service))
    plan(service)
    assert llm.requests[0]["format"] == SPECIALISTS[service].model_output.model_json_schema()


# SPC-09 (TP-SRS-075)
@pytest.mark.parametrize("service", SERVICES)
def test_prompt_says_not_live_or_bookable(plan, llm, service):
    llm.answer(answer_with(service))
    plan(service)
    assert NOT_LIVE_OR_BOOKABLE in llm.prompts[0]
    assert "not live" in NOT_LIVE_OR_BOOKABLE and "bookable" in NOT_LIVE_OR_BOOKABLE


# SPC-09: the prompt describes the trip.
@pytest.mark.parametrize("service", SERVICES)
def test_prompt_describes_trip(plan, llm, service):
    llm.answer(answer_with(service))
    plan(service, currency="eur")
    prompt = llm.prompts[0]
    for text in ("Manila", "Tokyo", "2026-12-01", "2026-12-06", "5 nights", "2 travellers", "1500", "EUR"):
        assert text in prompt


# SPC-09: budgets are written out in full, never in scientific notation.
@pytest.mark.parametrize("budget, text", [(1234567, "1234567"), (1500.5, "1500.50"), (99.99, "99.99")])
def test_prompt_budget_written_in_full(plan, llm, budget, text):
    llm.answer(answer_with("flight"))
    plan("flight", budget=budget)
    assert f"total budget {text} USD" in llm.prompts[0]


# SPC-10 (TP-SRS-076)
def test_activities_prompt_uses_preferences(plan, llm):
    llm.answer(answer_with("activities"))
    plan("activities", preferences=["museums", "street food"])
    assert "museums" in llm.prompts[0]
    assert "street food" in llm.prompts[0]
    assert "general sightseeing" not in llm.prompts[0]


# SPC-11 (TP-SRS-076)
def test_activities_prompt_defaults_to_general_sightseeing(plan, llm):
    llm.answer(answer_with("activities"))
    plan("activities")
    assert "general sightseeing" in llm.prompts[0]
