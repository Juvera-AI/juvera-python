"""HTTP exporter for Juvera SDK."""
from __future__ import annotations
import logging
import httpx
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from juvera_sdk.config import JuveraConfig

_logger = logging.getLogger("juvera_sdk")


def _otel_value(v) -> dict:
    """Convert a Python value to OTel attribute value format."""
    if isinstance(v, bool):
        return {"boolValue": v}
    if isinstance(v, int):
        return {"intValue": v}
    if isinstance(v, float):
        return {"doubleValue": v}
    return {"stringValue": str(v)}


def _attrs_list(attrs: dict | None) -> list[dict]:
    if not attrs:
        return []
    return [{"key": k, "value": _otel_value(v)} for k, v in attrs.items()]


class JuveraSpanExporter(SpanExporter):
    """
    Exports OTel spans to the Juvera ingest gateway as TraceIngestEnvelope JSON.
    One HTTP POST per export() call (batch).
    """

    def __init__(self, config: JuveraConfig):
        self._config = config

    def export(self, spans: list[ReadableSpan]) -> SpanExportResult:
        if not spans:
            return SpanExportResult.SUCCESS

        # Build resourceSpans grouped by trace_id (simple: one resource block)
        # Resource attrs come from the first span's resource
        resource = spans[0].resource
        resource_attrs = _attrs_list(dict(resource.attributes or {}))

        otel_spans = []
        for span in spans:
            attrs = _attrs_list(dict(span.attributes or {}))
            otel_spans.append({
                "traceId": format(span.context.trace_id, "032x"),
                "spanId": format(span.context.span_id, "016x"),
                "name": span.name,
                "startTimeUnixNano": str(span.start_time),
                "endTimeUnixNano": str(span.end_time or span.start_time),
                "attributes": attrs,
            })

        envelope = {
            "resourceSpans": [{
                "resource": {"attributes": resource_attrs},
                "scopeSpans": [{
                    "scope": {"name": "juvera-sdk"},
                    "spans": otel_spans,
                }],
            }]
        }

        try:
            resp = httpx.post(
                self._config.traces_url,
                json=envelope,
                headers={
                    "X-API-Key": self._config.api_key,
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            return SpanExportResult.SUCCESS
        except Exception as exc:
            _logger.warning("export failed: %s", exc)
            return SpanExportResult.FAILURE

    def shutdown(self) -> None:
        pass
