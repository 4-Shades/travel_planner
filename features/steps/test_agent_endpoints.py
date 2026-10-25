"""Steps for features/api/agent_endpoints.feature (BDD scenarios §4.1)."""

import json

from pytest_bdd import parsers, scenario, then, when

FEATURE = "api/agent_endpoints.feature"


@scenario(FEATURE, "Every agent exposes the standard endpoints")
def test_standard_endpoints():
    pass


@scenario(FEATURE, "The health check reports the service")
def test_health_check():
    pass


@scenario(FEATURE, "The health check never needs an API key")
def test_health_check_without_key():
    pass


@scenario(FEATURE, "The OpenAPI schema describes the run endpoint")
def test_openapi_schema():
    pass


@scenario(FEATURE, "An invalid request body is rejected with the invalid fields listed")
def test_invalid_body():
    pass


@scenario(FEATURE, "A request ID is logged and forwarded to every specialist")
def test_request_id_forwarded():
    pass


@when(parsers.parse('I post a valid travel request to the Host with the header "{name}: {value}"'), target_fixture="response")
def post_to_host_with_header(agent, travel_request, name, value):
    return agent.post("/run", json=travel_request, headers={name: value})


def log_ids(caplog, logger):
    return {r.request_id for r in caplog.records if r.name == logger}


@then(parsers.parse('the Host\'s log lines for the request include "{request_id}"'))
def host_logs_id(caplog, request_id):
    assert log_ids(caplog, "travel_planner.host") == {request_id}


@then(parsers.parse('the Flight, Stay, and Activities agents each receive the header "{name}: {value}"'))
def specialists_receive_header(specialists, name, value):
    for specialist in specialists.values():
        assert [headers[name] for headers in specialist.headers] == [value]


@then(parsers.parse('each specialist\'s log lines for the request include "{request_id}"'))
def specialists_log_id(caplog, request_id):
    for service in ("flight", "stay", "activities"):
        assert log_ids(caplog, f"travel_planner.{service}") == {request_id}


@then("it exposes these endpoints:")
def exposes_endpoints(agent, datatable):
    header, *rows = datatable
    assert header == ["method", "path"]
    for method, path in rows:
        response = agent.request(method, path, json={} if method == "POST" else None)
        assert response.status_code not in (404, 405), f"{method} {path}"


@then("the response body is:")
def response_body(response, docstring):
    assert response.json() == json.loads(docstring)


@then(parsers.parse('the schema describes "{method} {path}"'))
def schema_describes(response, method, path):
    assert method.lower() in response.json()["paths"][path]


@when(parsers.parse('I post this body to "{path}":'), target_fixture="response")
def post_body(agent, path, docstring):
    return agent.post(path, content=docstring.encode(), headers={"Content-Type": "application/json"})


@then(parsers.parse('the response lists the invalid fields "{first}" and "{second}"'))
def lists_invalid_fields(response, first, second):
    fields = {str(part) for error in response.json()["detail"] for part in error["loc"]}
    assert {first, second} <= fields
