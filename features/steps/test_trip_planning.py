"""Steps for features/api/trip_planning.feature (BDD scenarios §4.3)."""

import re

from pytest_bdd import given, parsers, scenarios, then, when

from features.conftest import SERVICES, Agent
from shared.schemas import SPECIALISTS
from tests.fakes.llm import OLLAMA_URL, OPENAI_URL

scenarios("api/trip_planning.feature")

PARTS = [contract.part for contract in SPECIALISTS.values()]


def quoted(text):
    return re.findall(r'"([^"]+)"', text)


@given(parsers.parse("the Host is running with DOWNSTREAM_TIMEOUT_SECONDS set to {seconds:d}"), target_fixture="agent")
def host_with_timeout(agent_app, seconds):
    # Model calls must time out before specialist calls do (TP-SRS-142).
    return Agent(agent_app, "host", DOWNSTREAM_TIMEOUT_SECONDS=str(seconds), LLM_TIMEOUT_SECONDS=str(seconds / 2))


@given("the specialists are fakes that record what they receive")
def specialists_are_fakes(specialists):
    assert set(specialists) == set(SPECIALISTS)


@given(parsers.parse("each specialist takes {seconds:g} seconds to answer"))
def each_specialist_slow(specialists, seconds):
    for specialist in specialists.values():
        specialist.answer_slowly(seconds)


@given(parsers.parse("the {name} agent cannot be reached"))
def agent_unreachable(specialists, name):
    specialists[SERVICES[name]].unreachable()


@given(parsers.parse("the {name} agent returns status {status:d}"))
def agent_fails(specialists, name, status):
    specialists[SERVICES[name]].fail(status)


@given(parsers.parse("the {name} agent returns invalid JSON"))
def agent_invalid_json(specialists, name):
    specialists[SERVICES[name]].answer_invalid_json()


@given(parsers.parse("the {name} agent returns JSON that does not match its response model"))
def agent_wrong_model(specialists, name):
    specialists[SERVICES[name]].answer_wrong_model()


@given(parsers.parse("the {name} agent takes {seconds:d} seconds to answer"))
def agent_slow(specialists, name, seconds):
    specialists[SERVICES[name]].answer_slowly(seconds)


@given("the other specialists answer normally")
def others_answer_normally():
    # Every fake answers normally unless a step has told it otherwise.
    pass


@given(parsers.parse("every specialist returns status {status:d}"))
def every_specialist_fails(specialists, status):
    for specialist in specialists.values():
        specialist.fail(status)


@given("the specialists return these sources:")
def specialists_return_sources(specialists, datatable):
    header, *rows = datatable
    assert header == ["agent", "title", "url", "license"]
    sources = {service: [] for service in specialists}
    for name, title, url, license_ in rows:
        entry = {"title": title, "license": license_}
        if url:
            entry["url"] = url
        sources[SERVICES[name]].append(entry)
    for service, entries in sources.items():
        specialists[service].answer_normally(sources=entries)


@given("every language-model provider address is watched", target_fixture="model_routes")
def watch_model_providers(fake_router):
    addresses = (OLLAMA_URL, OPENAI_URL, "http://localhost:11434", "https://api.openai.com")
    return [fake_router.route(url__startswith=address) for address in addresses]


@when(parsers.parse("I post a travel request with travellers set to {travellers:d}"), target_fixture="response")
def post_with_travellers(agent, travel_request, travellers):
    return agent.post("/run", json={**travel_request, "travellers": travellers})


@then(parsers.re(r"the plan has the fields (?P<fields>.+)"))
def plan_fields(response, fields):
    assert set(response.json()) == set(quoted(fields))


@then("the plan has flights, stays, and activities")
def plan_has_all_parts(response):
    assert all(response.json()[part] for part in PARTS)


@then("the plan's errors are empty")
def no_errors(response):
    assert response.json()["errors"] == []


@then(parsers.parse("the Host answers in less than {seconds:g} seconds"))
def answers_quickly(agent, seconds):
    assert agent.last_duration < seconds


@then("the Flight, Stay, and Activities agents each received the request once")
def each_received_once(specialists):
    assert all(len(specialist.requests) == 1 for specialist in specialists.values())


@then(parsers.parse('the plan\'s errors have one entry for "{part}" with message "{message}"'))
def one_error(response, part, message):
    assert response.json()["errors"] == [{"part": part, "message": message}]
    assert response.json()[part] == []


@then("the plan has offers in the other two parts")
def other_parts(response):
    body = response.json()
    failed = {error["part"] for error in body["errors"]}
    assert all(body[part] for part in PARTS if part not in failed)
    assert len(failed) == 1


@then(parsers.re(r"the plan's errors have one entry each for (?P<parts>.+)"))
def one_error_each(response, parts):
    assert sorted(error["part"] for error in response.json()["errors"]) == sorted(quoted(parts))


@then("the plan has no offers")
def no_offers(response):
    assert not any(response.json()[part] for part in PARTS)


@then("the plan's sources are:")
def plan_sources(response, datatable):
    header, *rows = datatable
    assert response.json()["sources"] == [dict(zip(header, row)) for row in rows]


@then("the Host makes no request to any language-model provider")
def no_model_requests(model_routes, language_model):
    assert not any(route.called for route in model_routes)
    assert language_model.requests == []


@then("no specialist receives a request")
def no_specialist_called(specialists):
    assert not any(specialist.route.called for specialist in specialists.values())
