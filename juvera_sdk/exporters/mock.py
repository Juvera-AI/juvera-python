"""Mock exporter for testing."""
from __future__ import annotations
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult


class MockExporter(SpanExporter):
    """Captures spans in memory. Use in tests — no network calls."""

    def __init__(self):
        self._spans: list[ReadableSpan] = []

    def export(self, spans: list[ReadableSpan]) -> SpanExportResult:
        self._spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass

    def span_count(self) -> int:
        return len(self._spans)

    def last_span(self) -> ReadableSpan | None:
        return self._spans[-1] if self._spans else None

    def all_spans(self) -> list[ReadableSpan]:
        return list(self._spans)

    def clear(self) -> None:
        self._spans.clear()
