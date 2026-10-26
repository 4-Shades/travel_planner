"""Steps for features/metrics/metrics.feature (BDD scenarios §6.1).

The OTLP endpoint is replaced by an exporter that keeps what it is sent, or rejects it.
"""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

import shared.telemetry
from features.conftest import SERVICES, Agent
from tests.fakes.index import GuidanceIndex
from tests.fakes.llm import FakeEmbedder
from tests.fakes.otlp import RecordingExporter

scenarios("metrics/metrics.feature")


class Telemetry:
    def __init__(self, agent_app):
        self.agent_app = agent_app
        self.agents = {}
        self.exporters = []

    def agent(self, service, **env):
        if service not in self.agents:
            self.agents[service] = Agent(self.agent_app, service, **env)
        return self.agents[service]

    def metrics(self, service):
        return self.agents[service].client.app.state.metrics

    def points(self, name):
        for service in self.agents:
            self.metrics(service).force_flush()
        return [point for exporter in self.exporters for point in exporter.points(name)]


@pytest.fixture
def telemetry(agent_app):
    telemetry = Telemetry(agent_app)
    yield telemetry
    for service in telemetry.agents:
        telemetry.metrics(service).shutdown()


def use_exporter(telemetry, monkeypatch, fail=False):
    def exporter():
        created = RecordingExporter(fail=fail)
        telemetry.exporters.append(created)
        return created

    monkeypatch.setattr(shared.telemetry, "otlp_exporter", exporter)


@given("OTEL_EXPORTER_OTLP_ENDPOINT is set")
def endpoint_set(telemetry, monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://otlp.test/otlp")
    use_exporter(telemetry, monkeypatch)


@given("OTEL_EXPORTER_OTLP_ENDPOINT is not set")
def endpoint_not_set(telemetry, monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    use_exporter(telemetry, monkeypatch)


@given("the metrics endpoint rejects every export")
def endpoint_rejects(telemetry, monkeypatch):
    use_exporter(telemetry, monkeypatch, fail=True)


@given("the Activities agent is running with retrieval enabled", target_fixture="agent")
def activities_with_retrieval(telemetry, tmp_path, fake_router):
    index = GuidanceIndex(tmp_path).build()
    FakeEmbedder(fake_router, "ollama", dimensions=8)
    return telemetry.agent("activities", **index.env())


@given("the language model returns status 500")
def model_fails(language_model):
    language_model.fail(500)


@given("the language model takes longer than LLM_TIMEOUT_SECONDS")
def model_times_out(language_model):
    language_model.time_out()


@when(parsers.parse("I post a valid travel request to the {name} agent"), target_fixture="response")
def post_to_agent(telemetry, travel_request, monkeypatch, name):
    if SERVICES[name] not in telemetry.agents:
        monkeypatch.setenv("RAG_ENABLED", "false")
    return telemetry.agent(SERVICES[name]).post("/run", json=travel_request)


@when("I post a valid travel request to the Host", target_fixture="response")
def post_to_host(telemetry, travel_request):
    return telemetry.agent("host").post("/run", json=travel_request)


@when("metrics are collected")
def collect(telemetry):
    for service in telemetry.agents:
        telemetry.metrics(service).force_flush()


@then(parsers.parse('they include HTTP request metrics for "{route}"'))
def http_metrics(telemetry, route):
    assert route in {a["http.route"] for a, _ in telemetry.points("http.server.request.duration")}


@then("they include the model call duration with its outcome")
def model_metrics(telemetry):
    assert {a["outcome"] for a, _ in telemetry.points("llm.call.duration")} == {"success"}


@then("they include token usage by type")
def token_metrics(telemetry):
    assert {a["type"] for a, _ in telemetry.points("llm.tokens")} == {"prompt", "completion"}


@then("they include the retrieval duration with its outcome")
def retrieval_metrics(telemetry):
    assert {a["outcome"] for a, _ in telemetry.points("rag.retrieval.duration")} == {"found"}


@then("metrics are exported at least once a minute")
def export_interval(telemetry):
    assert all(telemetry.metrics(service).export_interval_millis <= 60_000 for service in telemetry.agents)


@then(parsers.parse('a model call duration is recorded with outcome "{outcome}"'))
def model_outcome(telemetry, outcome):
    assert [a["outcome"] for a, _ in telemetry.points("llm.call.duration")] == [outcome]


@then("no metrics are sent")
def nothing_sent(telemetry):
    assert telemetry.exporters == []
    assert all(telemetry.metrics(service).provider is None for service in telemetry.agents)


@then("the export failure is logged")
def failure_logged(telemetry, caplog):
    for service in telemetry.agents:
        telemetry.metrics(service).force_flush()
    assert any(record.name.startswith("opentelemetry") and record.exc_info for record in caplog.records)
