"""Steps for features/api/request_validation.feature (BDD scenarios §4.2).

These steps all start "I post a valid travel request with ...", so each uses an exact
regular expression to keep it from matching another's text.
"""

import json
import uuid

from pytest_bdd import parsers, scenarios, then, when

scenarios("api/request_validation.feature")


def post(agent, body):
    return agent.post("/run", json=body)


@when(parsers.re(r"I post a valid travel request with a (?P<field>origin|destination) of (?P<length>\d+) characters$"), target_fixture="response")
def post_place_length(agent, travel_request, field, length):
    return post(agent, {**travel_request, field: "a" * int(length)})


@when(parsers.re(r'I post a valid travel request with start date "(?P<start>[^"]+)" and end date "(?P<end>[^"]+)"$'), target_fixture="response")
def post_dates(agent, travel_request, start, end):
    return post(agent, {**travel_request, "start_date": start, "end_date": end})


@when(parsers.re(r'I post a valid travel request with "(?P<field>\w+)" set to (?P<value>.+)$'), target_fixture="response")
def post_field_value(agent, travel_request, field, value):
    return post(agent, {**travel_request, field: json.loads(value)})


@when(parsers.re(r"I post a valid travel request with (?P<count>\d+) preferences$"), target_fixture="response")
def post_preferences(agent, travel_request, count):
    return post(agent, {**travel_request, "preferences": [f"interest {n}" for n in range(int(count))]})


@when(parsers.re(r"I post a valid travel request with a user_id of (?P<length>\d+) characters$"), target_fixture="response")
def post_user_id(agent, travel_request, length):
    return post(agent, {**travel_request, "user_id": "u" * int(length)})


@when(
    parsers.re(r'I post a valid travel request with origin "(?P<origin>[^"]+)", destination "(?P<destination>[^"]+)", and currency "(?P<currency>[^"]+)"$'),
    target_fixture="response",
)
def post_untidy(agent, travel_request, origin, destination, currency):
    return post(agent, {**travel_request, "origin": origin, "destination": destination, "currency": currency})


@when("I post a valid travel request without a request_id or trip_id", target_fixture="response")
def post_without_ids(agent, travel_request):
    return post(agent, {k: v for k, v in travel_request.items() if k not in ("request_id", "trip_id")})


@when(parsers.re(r'I post a valid travel request with request_id "(?P<request_id>[^"]+)" and trip_id "(?P<trip_id>[^"]+)"$'), target_fixture="response")
def post_with_ids(agent, travel_request, request_id, trip_id):
    return post(agent, {**travel_request, "request_id": request_id, "trip_id": trip_id})


@when("I post a valid travel request without a currency", target_fixture="response")
def post_without_currency(agent, travel_request):
    return post(agent, {k: v for k, v in travel_request.items() if k != "currency"})


@then(parsers.parse('the response lists the invalid field "{field}"'))
def lists_invalid_field(response, field):
    assert field in {str(part) for error in response.json()["detail"] for part in error["loc"]}


@then(parsers.parse('each specialist receives {field} "{value}"'))
def each_specialist_receives(specialists, field, value):
    for specialist in specialists.values():
        assert specialist.requests[-1][field] == value


@then(parsers.parse("the plan's {field} is a UUID"))
def plan_field_is_uuid(response, field):
    uuid.UUID(response.json()[field])


@then(parsers.parse('the plan\'s {field} is "{value}"'))
def plan_field_is(response, field, value):
    assert response.json()[field] == value
