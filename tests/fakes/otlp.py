"""A stand-in for the OTLP endpoint: an exporter that keeps what it is sent, or rejects it (TDD plan §2.3)."""

from opentelemetry.sdk.metrics.export import MetricExporter, MetricExportResult


class RecordingExporter(MetricExporter):
    def __init__(self, fail=False):
        super().__init__()
        self.fail = fail
        self.batches = []

    def export(self, metrics_data, timeout_millis=10_000, **kwargs):
        if self.fail:
            raise ConnectionError("the metrics endpoint rejected the export")
        self.batches.append(metrics_data)
        return MetricExportResult.SUCCESS

    def force_flush(self, timeout_millis=10_000):
        return True

    def shutdown(self, timeout_millis=30_000, **kwargs):
        pass

    def points(self, name):
        """(attributes, value or count) for every exported data point of the named metric."""
        found = []
        for data in self.batches:
            for resource_metrics in data.resource_metrics:
                for scope_metrics in resource_metrics.scope_metrics:
                    for metric in scope_metrics.metrics:
                        if metric.name == name:
                            for point in metric.data.data_points:
                                value = getattr(point, "value", getattr(point, "count", None))
                                found.append((dict(point.attributes), value))
        return found
