"""Steps for features/operations/performance.feature (BDD scenarios §6.2).

Only "Timeouts must nest" runs automatically; the other scenarios are @demonstration.
"""

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from agents.host.app import create_host_app
from shared.config import ConfigError, Settings


@scenario("operations/performance.feature", "Timeouts must nest")
def test_timeouts_must_nest():
    pass


@given(parsers.re(r"(?P<name>[A-Z_]+_SECONDS) is (?P<value>\d+)"))
def set_timeout(monkeypatch, name, value):
    monkeypatch.setenv(name, value)


@when("the Host starts", target_fixture="startup_error")
def host_starts():
    try:
        create_host_app(Settings.from_env())
    except ConfigError as error:
        return error
    return None


@then(parsers.parse("the configuration is {result}"))
def configuration_result(startup_error, result):
    if result == "accepted":
        assert startup_error is None
    elif result == "rejected":
        assert isinstance(startup_error, ConfigError)
    else:
        pytest.fail(f"Unknown result {result!r}")
