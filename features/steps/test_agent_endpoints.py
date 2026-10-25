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


# "A request ID is logged and forwarded to every specialist" is bound in phase 9,
# when the Host calls the specialists.


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
