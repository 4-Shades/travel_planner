"""Operational metrics, pushed over OTLP only when OTEL_EXPORTER_OTLP_ENDPOINT is set (TP-SRS-120 to TP-SRS-122).

The exporter reads its endpoint and any headers (such as Grafana Cloud's authorization) from the
standard OTEL_EXPORTER_OTLP_* variables. Exports run on a background thread, so a failed export is
logged by the OpenTelemetry SDK and never reaches a request (TP-SRS-122).
"""

import time

from opentelemetry.metrics import NoOpMeterProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

# At least once a minute (TP-SRS-120).
EXPORT_INTERVAL_MILLIS = 60_000


def otlp_exporter():
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter

    return OTLPMetricExporter()


class Metrics:
    def __init__(self, provider=None, export_interval_millis=None):
        # Without a provider every instrument is a no-op, so callers never need to check.
        self.provider = provider
        self.export_interval_millis = export_interval_millis
        meter = (provider or NoOpMeterProvider()).get_meter("travel_planner")
        self._requests = meter.create_histogram("http.server.request.duration", unit="s", description="HTTP requests handled")
        self._model_calls = meter.create_histogram("llm.call.duration", unit="s", description="Language-model calls")
        self._tokens = meter.create_counter("llm.tokens", unit="{token}", description="Language-model token usage")
        self._retrievals = meter.create_histogram("rag.retrieval.duration", unit="s", description="Guidance lookups")

    def record_request(self, route, method, status, seconds):
        self._requests.record(
            seconds, {"http.route": route, "http.request.method": method, "http.response.status_code": status}
        )

    def record_model_call(self, provider, outcome, seconds, prompt_tokens=0, completion_tokens=0):
        """outcome is success, error, timeout, or invalid (an answer that does not match the schema)."""
        self._model_calls.record(seconds, {"llm.provider": provider, "outcome": outcome})
        if prompt_tokens:
            self._tokens.add(prompt_tokens, {"type": "prompt"})
        if completion_tokens:
            self._tokens.add(completion_tokens, {"type": "completion"})

    def record_retrieval(self, outcome, seconds):
        """outcome is found, cached, skipped (not in the index), disabled, timeout, or error."""
        self._retrievals.record(seconds, {"outcome": outcome})

    def force_flush(self):
        if self.provider:
            self.provider.force_flush()

    def shutdown(self):
        if self.provider:
            self.provider.shutdown()


def create_metrics(service, settings, reader=None):
    """Metrics for one agent; reader adds a metric reader, for tests."""
    readers = [reader] if reader else []
    interval = None
    if settings.otel_endpoint:
        interval = EXPORT_INTERVAL_MILLIS
        readers.append(PeriodicExportingMetricReader(otlp_exporter(), export_interval_millis=interval))
    if not readers:
        # No endpoint: nothing is measured or sent (TP-SRS-121).
        return Metrics()
    resource = Resource.create({"service.name": f"travel-planner-{service}"})
    return Metrics(MeterProvider(resource=resource, metric_readers=readers), interval)


class MetricsMiddleware:
    """Records each HTTP request's route, method, status, and duration."""

    def __init__(self, app, metrics, routes):
        self.app = app
        self.metrics = metrics
        self.routes = routes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        start = time.perf_counter()
        status = 500

        async def send_with_status(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_with_status)
        finally:
            # Unknown paths share one label, so stray requests cannot multiply the series.
            route = scope["path"] if scope["path"] in self.routes() else "unmatched"
            self.metrics.record_request(route, scope["method"], status, time.perf_counter() - start)
