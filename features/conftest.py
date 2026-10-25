"""Fixtures and steps shared by the pytest-bdd scenarios (BDD scenarios §2.2).

Feature files go in features/<area>/, copied from docs/BEHAVIOR_DRIVEN_DEVELOPMENT_SCENARIOS.md,
and their step definitions in features/steps/. Each phase of docs/IMPLEMENTATION_GUIDE.md binds
the features it makes pass.
"""

import logging

import pytest
import respx
from pytest_bdd import given, parsers, then, when

from shared.schemas import SPECIALISTS
from tests import factories
from tests.asgi import AppClient
from tests.fakes.llm import PROVIDER_ENV, FakeLLM

SERVICES = {"Host": "host", "Flight": "flight", "Stay": "stay", "Activities": "activities"}


def pytest_bdd_apply_tag(tag, function):
    """Turn @TP-SRS-nnn tags into requirement markers instead of unregistered marker names."""
    if tag.startswith("TP-SRS-"):
        pytest.mark.requirement(tag)(function)
        return True
    return None


class LanguageModel:
    """Both fake providers at once; the agent uses whichever LLM_PROVIDER selects."""

    def __init__(self, router):
        self.fakes = {provider: FakeLLM(router, provider) for provider in PROVIDER_ENV}
        for fake in self.fakes.values():
            fake.answer_normally()

    def __getattr__(self, name):
        # answer(), fail(), time_out(), and the other FakeLLM settings apply to both providers.
        def apply(*args, **kwargs):
            for fake in self.fakes.values():
                getattr(fake, name)(*args, **kwargs)

        return apply

    @property
    def requests(self):
        return [body for fake in self.fakes.values() for body in fake.requests]

    @property
    def prompts(self):
        return [prompt for fake in self.fakes.values() for prompt in fake.prompts]


class Agent:
    """The agent under test, built on its first request so that later Given steps can still configure it."""

    def __init__(self, build, service, **env):
        self._build = build
        self.service = service
        self._env = env
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = AppClient(self._build(self.service, **self._env))
        return self._client

    def request(self, method, path, **kwargs):
        return self.client.request(method, path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)


@pytest.fixture(autouse=True)
def fake_router():
    """Every scenario runs against fakes; a route left unused is not an error."""
    with respx.mock(assert_all_called=False) as router:
        yield router


@pytest.fixture(autouse=True)
def language_model(fake_router, monkeypatch, caplog):
    for env in PROVIDER_ENV.values():
        for name, value in env.items():
            if name != "LLM_PROVIDER":
                monkeypatch.setenv(name, value)
    caplog.set_level(logging.INFO, logger="travel_planner")
    return LanguageModel(fake_router)


@pytest.fixture
def travel_request():
    """The scenario's travel request: "a valid travel request" until a step changes a field."""
    return factories.valid_request()


@given(parsers.parse("the {name} agent is running"), target_fixture="agent")
def agent_running(agent_app, name):
    return Agent(agent_app, SERVICES[name])


@given("the Host is running", target_fixture="agent")
def host_running(agent_app):
    return Agent(agent_app, "host")


@given(parsers.parse('the Host is running with HOST_API_KEY set to "{key}"'), target_fixture="agent")
def host_running_with_key(agent_app, key):
    return Agent(agent_app, "host", HOST_API_KEY=key)


@given("the Host is running without HOST_API_KEY", target_fixture="agent")
def host_running_without_key(agent_app):
    return Agent(agent_app, "host")


@given("the specialists answer normally")
def specialists_answer_normally():
    # Placeholder until phase 9, when the Host calls the specialists and this step
    # installs fake specialists that each return a valid answer.
    pass


@given("retrieval is disabled")
def retrieval_disabled(monkeypatch):
    monkeypatch.setenv("RAG_ENABLED", "false")


@given("the language model answers normally")
def language_model_answers_normally(language_model):
    language_model.answer_normally()


@given(parsers.parse('LLM_PROVIDER is "{provider}"'))
def llm_provider(monkeypatch, provider):
    monkeypatch.setenv("LLM_PROVIDER", provider)


@when('I post a valid travel request without an "X-API-Key" header', target_fixture="response")
def post_valid_request_without_key(agent, travel_request):
    return agent.post("/run", json=travel_request)


@when(parsers.parse('I post a valid travel request with the header "{name}: {value}"'), target_fixture="response")
def post_valid_request_with_header(agent, travel_request, name, value):
    return agent.post("/run", json=travel_request, headers={name: value})


@when('I post an invalid travel request without an "X-API-Key" header', target_fixture="response")
def post_invalid_request_without_key(agent, travel_request):
    return agent.post("/run", json={**travel_request, "origin": "M", "travellers": 0})


@when(parsers.parse("I post a valid travel request to the {name} agent"), target_fixture="response")
def post_valid_request_to(agent, travel_request, name):
    assert agent.service == SERVICES[name]
    return agent.post("/run", json=travel_request)


@when(parsers.parse('I request "{method} {path}"'), target_fixture="response")
def request_endpoint(agent, method, path):
    return agent.request(method, path)


@when(parsers.parse('I request "{method} {path}" without an "X-API-Key" header'), target_fixture="response")
def request_endpoint_without_key(agent, method, path):
    return agent.request(method, path)


@then(parsers.parse("the response status is {status:d}"))
def response_status(response, status):
    assert response.status_code == status


@then(parsers.parse('the response body does not contain "{text}"'))
def response_body_lacks(response, text):
    assert text not in response.text


@then("the response has at least one offer")
def response_has_offer(agent, response):
    assert response.status_code == 200
    assert response.json()[SPECIALISTS[agent.service].part]


@then(parsers.parse('the prompt includes "{first}" and "{second}"'))
def prompt_includes_both(language_model, first, second):
    assert first in language_model.prompts[-1]
    assert second in language_model.prompts[-1]


@then(parsers.re(r'the prompt includes "(?P<text>[^"]*)"$'))
def prompt_includes(language_model, text):
    assert text in language_model.prompts[-1]


@then(parsers.parse('the prompt does not include "{text}"'))
def prompt_lacks(language_model, text):
    assert text not in language_model.prompts[-1]
