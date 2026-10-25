"""Fixtures and steps shared by the pytest-bdd scenarios (BDD scenarios §2.2).

Feature files go in features/<area>/, copied from BEHAVIOR_DRIVEN_DEVELOPMENT_SCENARIOS.md,
and their step definitions in features/steps/. Each phase of IMPLEMENTATION_GUIDE.md binds
the features it makes pass.
"""

import pytest
from pytest_bdd import given, parsers, then, when

from tests import factories
from tests.asgi import AppClient

SERVICES = {"Host": "host", "Flight": "flight", "Stay": "stay", "Activities": "activities"}


def pytest_bdd_apply_tag(tag, function):
    """Turn @TP-SRS-nnn tags into requirement markers instead of unregistered marker names."""
    if tag.startswith("TP-SRS-"):
        pytest.mark.requirement(tag)(function)
        return True
    return None


@pytest.fixture
def travel_request():
    """The scenario's travel request: "a valid travel request" until a step changes a field."""
    return factories.valid_request()


@given(parsers.parse("the {name} agent is running"), target_fixture="agent")
def agent_running(agent_app, name):
    return AppClient(agent_app(SERVICES[name]))


@given("the Host is running", target_fixture="agent")
def host_running(agent_app):
    return AppClient(agent_app("host"))


@given(parsers.parse('the Host is running with HOST_API_KEY set to "{key}"'), target_fixture="agent")
def host_running_with_key(agent_app, key):
    return AppClient(agent_app("host", HOST_API_KEY=key))


@given("the Host is running without HOST_API_KEY", target_fixture="agent")
def host_running_without_key(agent_app):
    return AppClient(agent_app("host"))


@given("the specialists answer normally")
def specialists_answer_normally():
    # Placeholder until phase 9, when the Host calls the specialists and this step
    # installs fake specialists that each return a valid answer.
    pass


@when('I post a valid travel request without an "X-API-Key" header', target_fixture="response")
def post_valid_request_without_key(agent, travel_request):
    return agent.post("/run", json=travel_request)


@when(parsers.parse('I post a valid travel request with the header "{name}: {value}"'), target_fixture="response")
def post_valid_request_with_header(agent, travel_request, name, value):
    return agent.post("/run", json=travel_request, headers={name: value})


@when('I post an invalid travel request without an "X-API-Key" header', target_fixture="response")
def post_invalid_request_without_key(agent, travel_request):
    return agent.post("/run", json={**travel_request, "origin": "M", "travellers": 0})


@then(parsers.parse('the response body does not contain "{text}"'))
def response_body_lacks(response, text):
    assert text not in response.text


@when(parsers.parse('I request "{method} {path}"'), target_fixture="response")
def request_endpoint(agent, method, path):
    return agent.request(method, path)


@when(parsers.parse('I request "{method} {path}" without an "X-API-Key" header'), target_fixture="response")
def request_endpoint_without_key(agent, method, path):
    return agent.request(method, path)


@then(parsers.parse("the response status is {status:d}"))
def response_status(response, status):
    assert response.status_code == status
