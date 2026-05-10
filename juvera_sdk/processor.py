"""JuveraSpanProcessor — single source of truth for span processing."""
from __future__ import annotations
from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    SpanExporter,
)
from opentelemetry.trace import StatusCode
from juvera_sdk.compliance.pii import scan_span_for_pii, warn_pii
from juvera_sdk.exporters.debug import DebugExporter
from juvera_sdk.exporters.http import JuveraSpanExporter
from juvera_sdk.config import JuveraConfig
from juvera_sdk.normalizer import normalize_span_attributes, NormalizedSpan


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

        self._reset_stats()

    def _reset_stats(self):
        self._stats = {
            "span_count": 0,
            "tool_count": 0,
            "handoff_count": 0,
            "error_count": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "model": None,
            "provider": None,
            "work_item_id": None,
            "workflow_type": None,
            "pii_warnings": 0,
        }

    def on_start(self, span, parent_context=None):
        pass

    def on_end(self, span: ReadableSpan):
        if self._pii_check:
            matches = scan_span_for_pii(span)
            if matches:
                warn_pii(span, matches)
                self._stats["pii_warnings"] += len(matches)

        # Normalize third-party attributes
        normalized = normalize_span_attributes(span)
        if normalized is not None:
            span = NormalizedSpan(span, normalized)

        # Accumulate stats
        attrs = dict(span.attributes or {})
        span_name = span.name

        if span_name == "agent.run":
            self._stats["span_count"] += 1
            model = attrs.get("gen_ai.request.model")
            if model:
                self._stats["model"] = model
            provider = attrs.get("gen_ai.system")
            if provider:
                self._stats["provider"] = provider
            wid = attrs.get("juvera.work_item_id")
            if wid:
                self._stats["work_item_id"] = wid
            wf = attrs.get("juvera.workflow_type")
            if wf:
                self._stats["workflow_type"] = wf
            self._stats["input_tokens"] += attrs.get("gen_ai.usage.input_tokens", 0)
            self._stats["output_tokens"] += attrs.get("gen_ai.usage.output_tokens", 0)

            if hasattr(span, 'status') and span.status and span.status.status_code == StatusCode.ERROR:
                self._stats["error_count"] += 1

            for event in (span.events or []):
                if event.name == "tool.call":
                    self._stats["tool_count"] += 1

        elif span_name == "agent.handoff":
            self._stats["handoff_count"] += 1

        self._inner.on_end(span)

    def shutdown(self):
        self._inner.shutdown()

    def force_flush(self, timeout_millis=None):
        if timeout_millis is not None:
            self._inner.force_flush(timeout_millis)
        else:
            self._inner.force_flush()
        if self._is_debug and self._stats["span_count"] > 0:
            self.print_summary()
            self._reset_stats()

    def print_summary(self):
        s = self._stats
        cost = self._compute_cost()

        lines = []
        lines.append("")
        lines.append("=" * 50)
        lines.append("  Juvera Run Summary")
        lines.append("=" * 50)
        lines.append(f"  Spans: {s['span_count']}  |  Tools: {s['tool_count']}  |  Handoffs: {s['handoff_count']}  |  Errors: {s['error_count']}")

        if s["model"]:
            token_str = f"{s['input_tokens']} in / {s['output_tokens']} out"
            lines.append(f"  Model: {s['model']}  |  Tokens: {token_str}")

        if cost > 0:
            from juvera_sdk._fmt import fmt_cost, fmt_savings
            lines.append(f"  Estimated cost: {fmt_cost(cost)}")

        if s["workflow_type"]:
            from juvera_sdk.roi import WORKFLOW_BASELINES
            baseline = WORKFLOW_BASELINES.get(s["workflow_type"])
            if baseline:
                from juvera_sdk._fmt import fmt_cost, fmt_savings
                baseline_cost = baseline["human_cost_usd"]
                savings = baseline_cost - cost
                lines.append(f"  ROI estimate: {fmt_savings(savings)} savings  |  {fmt_cost(baseline_cost)} baseline  |  {s['workflow_type']}")

        lines.append("=" * 50)
        lines.append("")
        print("\n".join(lines))

    def _compute_cost(self) -> float:
        s = self._stats
        if (s["model"] or s["provider"]) and (s["input_tokens"] or s["output_tokens"]):
            from juvera_sdk.costs import estimate_token_cost_usd

            cost, _ = estimate_token_cost_usd(
                model=s.get("model"),
                provider=s.get("provider"),
                input_tokens=s["input_tokens"],
                output_tokens=s["output_tokens"],
            )
            return cost
        return 0.0
