"""JuveraSpanProcessor — single source of truth for span processing."""
from __future__ import annotations
from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    SpanExporter,
)
from juvera_sdk.compliance.pii import scan_span_for_pii, warn_pii
from juvera_sdk.exporters.debug import DebugExporter
from juvera_sdk.exporters.http import JuveraSpanExporter
from juvera_sdk.config import JuveraConfig


class JuveraSpanProcessor(SpanProcessor):
    """Standard OTel SpanProcessor for Juvera.

    Two entry points:
      1. j.init() creates a TracerProvider and adds this processor
      2. Attach mode: user adds this to their own TracerProvider

    Never calls trace.set_tracer_provider().
    """

    def __init__(
        self,
        api_key: str,
        org_id: str,
        endpoint: str = "https://ingest.juvera.ai",
        debug: bool = False,
        domain: str | None = None,
        pii_check: bool = True,
        _exporter: SpanExporter | None = None,
    ):
        if not api_key:
            raise ValueError("api_key is required")
        if not org_id:
            raise ValueError("org_id is required")

        self._is_local = (endpoint == "local")
        self._is_debug = debug or self._is_local
        self._pii_check = pii_check and self._is_debug

        if _exporter is not None:
            exporter = _exporter
        elif self._is_local:
            exporter = DebugExporter()
        else:
            config = JuveraConfig(
                api_key=api_key, org_id=org_id, endpoint=endpoint,
                domain=domain, debug=debug,
            )
            exporter = JuveraSpanExporter(config)

        if self._is_debug or _exporter is not None:
            self._inner = SimpleSpanProcessor(exporter)
        else:
            self._inner = BatchSpanProcessor(exporter)

    def on_start(self, span, parent_context=None):
        pass

    def on_end(self, span: ReadableSpan):
        if self._pii_check:
            matches = scan_span_for_pii(span)
            if matches:
                warn_pii(span, matches)
        self._inner.on_end(span)

    def shutdown(self):
        self._inner.shutdown()

    def force_flush(self, timeout_millis=None):
        if timeout_millis is not None:
            self._inner.force_flush(timeout_millis)
        else:
            self._inner.force_flush()
