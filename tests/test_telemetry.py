"""Metrics over OTLP (TDD plan, iteration 10)."""

import logging

import pytest
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

import shared.telemetry
from shared.telemetry import EXPORT_INTERVAL_MILLIS, create_metrics
from tests import factories
from tests.asgi import AppClient
from tests.fakes.agents import AGENT_ENV, FakeAgent
from tests.fakes.index import GuidanceIndex
from tests.fakes.llm import PROVIDER_ENV, FakeEmbedder, FakeLLM
from tests.fakes.otlp import RecordingExporter

pytestmark = pytest.mark.respx(assert_all_called=False)


@pytest.fixture
def reader():
    return InMemoryMetricReader()


@pytest.fixture
def llm(respx_mock):
    fake = FakeLLM(respx_mock, "ollama")
    fake.answer_normally()
    return fake


@pytest.fixture
def specialist(agent_app, settings, reader, llm):
    """A specialist app whose metrics go to the in-memory reader."""

    def build(service="flight", metric_reader=None, **env):
        env = {**PROVIDER_ENV["ollama"], "RAG_ENABLED": "false", **env}
        # A reader belongs to one meter provider, so a second app in a test needs its own.
        metrics = create_metrics(service, settings(**env), reader=metric_reader or reader)
        return AppClient(agent_app(service, metrics=metrics, **env))

    return build


def points(reader, name):
    """(attributes, value or count) for every data point of the named metric."""
    data = reader.get_metrics_data()
    found = []
    for resource_metrics in data.resource_metrics if data else []:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                if metric.name == name:
                    for point in metric.data.data_points:
                        found.append((dict(point.attributes), getattr(point, "value", getattr(point, "count", None))))
    return found


# TEL-01 (TP-SRS-121)
def test_no_endpoint_no_metrics(settings, monkeypatch):
    created = []
    monkeypatch.setattr(shared.telemetry, "otlp_exporter", lambda: created.append(1))
    metrics = create_metrics("host", settings())
    metrics.record_request("/run", "POST", 200, 0.1)
    assert metrics.provider is None
    assert created == []


# TEL-02 (TP-SRS-120)
def test_export_interval_at_most_one_minute(settings, monkeypatch):
    exporter = RecordingExporter()
    monkeypatch.setattr(shared.telemetry, "otlp_exporter", lambda: exporter)
    metrics = create_metrics("host", settings(OTEL_EXPORTER_OTLP_ENDPOINT="https://otlp.test/otlp"))
    try:
        assert metrics.export_interval_millis == EXPORT_INTERVAL_MILLIS <= 60_000
        metrics.record_request("/run", "POST", 200, 0.1)
        metrics.force_flush()
        assert exporter.batches
    finally:
        metrics.shutdown()


# TEL-02: the exporter sends to the configured endpoint over OTLP/HTTP.
def test_otlp_exporter_uses_configured_endpoint(monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://otlp.test/otlp")
    exporter = shared.telemetry.otlp_exporter()
    assert exporter._endpoint == "https://otlp.test/otlp/v1/metrics"


# TEL-03 (TP-SRS-120)
def test_http_request_metrics(specialist, reader):
    client = specialist()
    client.post("/run", json=factories.valid_request())
    client.get("/healthz")
    client.get("/no-such-page")
    recorded = {
        (a["http.route"], a["http.request.method"], a["http.response.status_code"]): count
        for a, count in points(reader, "http.server.request.duration")
    }
    assert recorded == {("/run", "POST", 200): 1, ("/healthz", "GET", 200): 1, ("unmatched", "GET", 404): 1}


# TEL-03: the Host records HTTP request metrics too.
def test_host_http_request_metrics(agent_app, settings, reader, respx_mock, monkeypatch):
    for service in ("flight", "stay", "activities"):
        FakeAgent(respx_mock, service)
    metrics = create_metrics("host", settings(**AGENT_ENV), reader=reader)
    AppClient(agent_app("host", metrics=metrics, **AGENT_ENV)).post("/run", json=factories.valid_request())
    assert [a["http.route"] for a, _ in points(reader, "http.server.request.duration")] == ["/run"]


# TEL-04 (TP-SRS-120)
@pytest.mark.parametrize(
    "setup, outcome",
    [
        (lambda llm: llm.answer_normally(), "success"),
        (lambda llm: llm.fail(500), "error"),
        (lambda llm: llm.time_out(), "timeout"),
        (lambda llm: llm.answer({"flights": [{"airline": "No price"}]}), "invalid"),
    ],
)
def test_model_call_duration_by_outcome(specialist, reader, llm, setup, outcome):
    setup(llm)
    specialist().post("/run", json=factories.valid_request())
    assert [a["outcome"] for a, _ in points(reader, "llm.call.duration")] == [outcome]
    assert all(a["llm.provider"] == "ollama" for a, _ in points(reader, "llm.call.duration"))


# TEL-05 (TP-SRS-120)
def test_token_usage_by_type(specialist, reader, llm):
    llm.route.mock(side_effect=None)
    llm.answer({"flights": [factories.flight_offer()]}, prompt_tokens=120, completion_tokens=45)
    specialist().post("/run", json=factories.valid_request())
    assert {a["type"]: value for a, value in points(reader, "llm.tokens")} == {"prompt": 120, "completion": 45}


# TEL-06 (TP-SRS-120)
@pytest.mark.parametrize(
    "destination, setup, outcome",
    [
        ("Tokyo", None, "found"),
        ("Atlantis", None, "skipped"),
        ("Tokyo", lambda embedder: embedder.fail(500), "error"),
        ("Tokyo", "slow", "timeout"),
    ],
)
def test_retrieval_duration_by_outcome(specialist, reader, respx_mock, tmp_path, today, monkeypatch, destination, setup, outcome):
    index = GuidanceIndex(tmp_path).build()
    embedder = FakeEmbedder(respx_mock, "ollama", dimensions=8)
    if setup == "slow":
        async def slow_embed(self, texts):
            import asyncio

            await asyncio.sleep(5)

        monkeypatch.setattr("shared.llm.OllamaClient.embed", slow_embed)
    elif setup:
        setup(embedder)
    client = specialist("activities", **index.env(), RAG_TIMEOUT_SECONDS="0.2")
    client.post("/run", json=factories.valid_request(destination=destination))
    assert [a["outcome"] for a, _ in points(reader, "rag.retrieval.duration")] == [outcome]


# TEL-06: a cached lookup and a disabled retriever have their own outcomes.
def test_retrieval_cached_and_disabled_outcomes(specialist, reader, respx_mock, tmp_path, today):
    index = GuidanceIndex(tmp_path).build()
    FakeEmbedder(respx_mock, "ollama", dimensions=8)
    client = specialist("activities", **index.env())
    client.post("/run", json=factories.valid_request())
    client.post("/run", json=factories.valid_request())
    assert sorted(a["outcome"] for a, _ in points(reader, "rag.retrieval.duration")) == ["cached", "found"]

    disabled_reader = InMemoryMetricReader()
    specialist("activities", metric_reader=disabled_reader, RAG_ENABLED="false").post("/run", json=factories.valid_request())
    assert [a["outcome"] for a, _ in points(disabled_reader, "rag.retrieval.duration")] == ["disabled"]


# TEL-07 (TP-SRS-122)
def test_export_failure_does_not_affect_requests(agent_app, settings, respx_mock, monkeypatch, caplog):
    for service in ("flight", "stay", "activities"):
        FakeAgent(respx_mock, service)
    monkeypatch.setattr(shared.telemetry, "otlp_exporter", lambda: RecordingExporter(fail=True))
    env = {**AGENT_ENV, "OTEL_EXPORTER_OTLP_ENDPOINT": "https://otlp.test/otlp"}
    metrics = create_metrics("host", settings(**env))
    try:
        response = AppClient(agent_app("host", metrics=metrics, **env)).post("/run", json=factories.valid_request())
        assert response.status_code == 200
        caplog.set_level(logging.WARNING)
        metrics.force_flush()
        assert any("rejected the export" in r.getMessage() or r.exc_info for r in caplog.records)
    finally:
        metrics.shutdown()
