"""Steps for features/api/suggestion_generation.feature (BDD scenarios §4.4)."""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from agents.specialist import NOT_LIVE_OR_BOOKABLE
from shared.schemas import SPECIALISTS
from tests import factories
from tests.fakes.llm import OPENAI_KEY

from features.conftest import SERVICES

scenarios("api/suggestion_generation.feature")


def offers_answer(service, **overrides):
    return {SPECIALISTS[service].part: [factories.OFFERS[service](**overrides)]}


@given(parsers.parse("the language model answers with valid {name} offers"))
def model_answers_valid_offers(language_model, name):
    language_model.answer(offers_answer(SERVICES[name]))


@given("the language model returns status 500")
def model_fails(language_model):
    language_model.fail(500)


@given("the language model takes longer than LLM_TIMEOUT_SECONDS")
def model_times_out(language_model):
    language_model.time_out()


@given("the language model refuses the request")
def model_refuses(language_model, monkeypatch):
    # Only OpenAI reports refusals, so this scenario runs the agent against OpenAI.
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    language_model.fakes["openai"].refuse()


@given("the language model answers with text that is not JSON")
def model_answers_text(language_model):
    language_model.answer_text("Here are some ideas for your trip!")


@given(parsers.parse("the language model answers with an offer priced at {price:d}"))
def model_answers_negative_price(language_model, agent, price):
    language_model.answer(offers_answer(agent.service, price=price))


@given(parsers.parse('the language model answers with an offer in currency "{currency}"'))
def model_answers_bad_currency(language_model, agent, currency):
    language_model.answer(offers_answer(agent.service, currency=currency))


@given("the language model answers with no offers and no error")
def model_answers_nothing(language_model, agent):
    language_model.answer({SPECIALISTS[agent.service].part: []})


@when(parsers.parse('I post a valid travel request with preferences "{first}" and "{second}"'), target_fixture="response")
def post_with_preferences(agent, travel_request, first, second):
    return agent.post("/run", json={**travel_request, "preferences": [first, second]})


@when("I post a valid travel request without preferences", target_fixture="response")
def post_without_preferences(agent, travel_request):
    return agent.post("/run", json={key: value for key, value in travel_request.items() if key != "preferences"})


@then(parsers.parse("every offer matches the {name} response model"))
def offers_match_model(response, name):
    SPECIALISTS[SERVICES[name]].response.model_validate(response.json())


@then(parsers.parse("the language-model request asks for JSON matching the {name} response schema"))
def request_asks_for_schema(language_model, name):
    body = language_model.requests[-1]
    expected = SPECIALISTS[SERVICES[name]].model_output.model_json_schema()
    if "format" in body:
        assert body["format"] == expected
    else:
        json_schema = body["response_format"]["json_schema"]
        assert json_schema["strict"] is True
        assert json_schema["schema"]["properties"].keys() == expected["properties"].keys()


@then("the language-model request sets temperature to 0")
def request_temperature_zero(language_model):
    body = language_model.requests[-1]
    assert body.get("temperature", body.get("options", {}).get("temperature")) == 0


@then(parsers.parse('the response error is "{message}"'))
def response_error(response, message):
    assert response.status_code == 200
    assert response.json()["error"] == message


@then("the response mentions no provider name, stack trace, or key")
def response_reveals_nothing(response):
    for text in ("Ollama", "OpenAI", "ollama", "openai", "Traceback", OPENAI_KEY):
        assert text not in response.text


@then("the agent logs the underlying cause")
def agent_logs_cause(caplog):
    causes = [
        record.getMessage().removeprefix("Planning failed: ")
        for record in caplog.records
        if record.name.startswith("travel_planner") and record.getMessage().startswith("Planning failed: ")
    ]
    assert causes and all(cause.split(":")[0] in ("LLMError", "LLMTimeout", "ValidationError") for cause in causes)


@then("the prompt tells the model not to present suggestions as live or bookable")
def prompt_not_bookable(language_model):
    assert NOT_LIVE_OR_BOOKABLE in language_model.prompts[-1]


@then(parsers.parse("the model request goes to {endpoint}"))
def model_request_endpoint(language_model, endpoint):
    providers = {"the Ollama chat endpoint": "ollama", "the OpenAI chat completions endpoint": "openai"}
    if endpoint not in providers:
        pytest.fail(f"Unknown endpoint {endpoint!r}")
    used = {provider for provider, fake in language_model.fakes.items() if fake.route.called}
    assert used == {providers[endpoint]}
