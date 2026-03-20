# juvera_sdk/span.py
from __future__ import annotations
import uuid
from contextlib import contextmanager
from opentelemetry import trace
from juvera_sdk import context as _ctx
import juvera_sdk.tracer as _tracer


class AgentSpan:
    """Wraps an OTel span with Juvera-specific helpers."""

    def __init__(self, otel_span: trace.Span, work_item_id: str):
        self._span = otel_span
        self.work_item_id = work_item_id

    def set_model(self, model: str, provider: str | None = None) -> None:
        self._span.set_attribute("gen_ai.request.model", model)
        if provider:
            self._span.set_attribute("gen_ai.system", provider)

    def set_tokens(self, input: int = 0, output: int = 0) -> None:
        self._span.set_attribute("gen_ai.usage.input_tokens", input)
        self._span.set_attribute("gen_ai.usage.output_tokens", output)

    def add_tool_call(self, tool_name: str, status: str = "success") -> None:
        self._span.add_event("tool.call", {
            "tool.name": tool_name,
            "tool.status": status,
        })

    def set_error(self, error: Exception) -> None:
        self._span.set_status(trace.StatusCode.ERROR, str(error))
        self._span.record_exception(error)

    def set_attribute(self, key: str, value) -> None:
        self._span.set_attribute(key, value)


@contextmanager
def agent_span(
    agent_id: str,
    domain: str | None = None,
    work_item_id: str | None = None,
    workflow_type: str | None = None,
    business_unit: str | None = None,
):
    """Context manager for an agent work item. Yields an AgentSpan."""
    from juvera_sdk import _get_config
    config = _get_config()

    wid = work_item_id or str(uuid.uuid4())
    eff_domain = domain or config.domain

    tracer = _tracer.get_tracer()
    with tracer.start_as_current_span("agent.run") as otel_span:
        otel_span.set_attribute("juvera.agent_id", agent_id)
        otel_span.set_attribute("juvera.work_item_id", wid)
        if eff_domain:
            otel_span.set_attribute("juvera.domain", eff_domain)
        if workflow_type:
            otel_span.set_attribute("juvera.workflow_type", workflow_type)
        if business_unit:
            otel_span.set_attribute("juvera.business_unit", business_unit)

        wid_token = _ctx._work_item_id.set(wid)
        aid_token = _ctx._agent_id.set(agent_id)
        try:
            yield AgentSpan(otel_span, wid)
        finally:
            _ctx._work_item_id.reset(wid_token)
            _ctx._agent_id.reset(aid_token)
