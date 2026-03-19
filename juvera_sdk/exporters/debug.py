"""Debug exporter for local development."""
from __future__ import annotations
import json
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult


class DebugExporter(SpanExporter):
    """Prints spans to stdout. Activated by endpoint='local'."""

    def export(self, spans: list[ReadableSpan]) -> SpanExportResult:
        for span in spans:
            attrs = dict(span.attributes or {})
            print(f"[juvera-debug] SPAN name={span.name!r} "
                  f"trace_id={format(span.context.trace_id, '032x')} "
                  f"agent_id={attrs.get('juvera.agent_id')} "
                  f"work_item_id={attrs.get('juvera.work_item_id')} "
                  f"attrs={json.dumps(attrs, default=str)}")
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass
