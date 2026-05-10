# juvera_sdk/span.py
from __future__ import annotations
import importlib
import json
import uuid
from contextlib import contextmanager
from opentelemetry import trace
import juvera_sdk.tracer as _tracer

_ctx = importlib.import_module("juvera_sdk.context")


class AgentSpan:
    """Wraps an OTel span with Juvera-specific helpers."""

    def __init__(self, otel_span: trace.Span, work_item_id: str):
        self._span = otel_span
        self.work_item_id = work_item_id

    def _set_capture_state(self, readiness: str) -> None:
        self._span.set_attribute("juvera.instrumentation_readiness", readiness)
        self._span.set_attribute("juvera.provisional", readiness == "provisional")

    def set_model(self, model: str, provider: str | None = None) -> None:
        self._span.set_attribute("gen_ai.request.model", model)
        if provider:
            self._span.set_attribute("gen_ai.system", provider)

    def set_tokens(self, input: int = 0, output: int = 0, cache_read: int = 0, cache_creation: int = 0, reasoning: int = 0) -> None:
        self._span.set_attribute("gen_ai.usage.input_tokens", input)
        self._span.set_attribute("gen_ai.usage.output_tokens", output)
        if cache_read:
            self._span.set_attribute("gen_ai.usage.cache_read_tokens", cache_read)
        if cache_creation:
            self._span.set_attribute("gen_ai.usage.cache_creation_tokens", cache_creation)
        if reasoning:
            self._span.set_attribute("gen_ai.usage.reasoning_tokens", reasoning)

    def set_prompt(self, text: str) -> None:
        self._span.set_attribute("gen_ai.prompt", text)

    def set_completion(self, text: str) -> None:
        self._span.set_attribute("gen_ai.completion", text)

    def set_latency(self, latency_ms: int | float) -> None:
        self._span.set_attribute("juvera.latency_ms", latency_ms)
        self._span.set_attribute("gen_ai.response.duration_ms", latency_ms)

    def set_context_window(
        self,
        *,
        used_tokens: int | None = None,
        limit_tokens: int | None = None,
        truncated: bool | None = None,
        limit_exceeded: bool | None = None,
    ) -> None:
        if used_tokens is not None:
            self._span.set_attribute("juvera.context_window.used_tokens", int(used_tokens))
        if limit_tokens is not None:
            self._span.set_attribute("juvera.context_window.limit_tokens", int(limit_tokens))
        if truncated is not None:
            self._span.set_attribute("juvera.context_window.truncated", bool(truncated))
        if limit_exceeded is not None:
            self._span.set_attribute("juvera.context_window.limit_exceeded", bool(limit_exceeded))

    def mark_timeout(self, timeout: bool = True) -> None:
        self._span.set_attribute("juvera.timeout", bool(timeout))

    def mark_malformed_prompt(self, malformed: bool = True) -> None:
        self._span.set_attribute("juvera.prompt.malformed", bool(malformed))

    def set_routing_decision(self, decision: str) -> None:
        self._span.set_attribute("juvera.routing.decision", decision)

    def add_context_source(
        self,
        name: str,
        doc_type: str | None = None,
        token_count: int | None = None,
    ) -> None:
        event_attrs: dict[str, str | int] = {"context.source.name": name}
        if doc_type is not None:
            event_attrs["context.source.doc_type"] = doc_type
        if token_count is not None:
            event_attrs["context.source.token_count"] = token_count
        self._span.add_event("context.source", event_attrs)

    def add_tool_call(
        self,
        tool_name: str,
        status: str = "success",
        duration_ms: int | None = None,
        error: str | None = None,
    ) -> None:
        event_attrs: dict[str, str | int] = {
            "tool.name": tool_name,
            "tool.status": status,
        }
        if duration_ms is not None:
            event_attrs["tool.duration_ms"] = duration_ms
        if error is not None:
            event_attrs["tool.error"] = error
        self._span.add_event("tool.call", event_attrs)

    def set_error(self, error: Exception) -> None:
        self._span.set_status(trace.StatusCode.ERROR, str(error))
        self._span.record_exception(error)

    def set_attribute(self, key: str, value) -> None:
        self._span.set_attribute(key, value)

    def set_experiment(
        self,
        experiment_id: str,
        variant_id: str,
        *,
        variant_label: str | None = None,
        prompt_version: str | None = None,
        release_label: str | None = None,
        assignment_mode: str | None = None,
        subject_key: str | None = None,
        assignment_reason: str | None = None,
        assignment_timestamp: str | None = None,
        exposure_event: str | None = None,
        config_ref: str | None = None,
        experiment_name: str | None = None,
        is_control: bool | None = None,
    ) -> None:
        metadata = {
            "experiment_id": experiment_id,
            "variant_id": variant_id,
            "variant_label": variant_label,
            "prompt_version": prompt_version,
            "release_label": release_label,
            "assignment_mode": assignment_mode,
            "subject_key": subject_key,
            "assignment_reason": assignment_reason,
            "assignment_timestamp": assignment_timestamp,
            "exposure_event": exposure_event,
            "config_ref": config_ref,
            "experiment_name": experiment_name,
            "is_control": str(is_control).lower() if is_control is not None else None,
        }
        for key, value in metadata.items():
            if value is None:
                continue
            self._span.set_attribute(f"juvera.properties.{key}", value)
        subject_key = subject_key or _ctx.get_subject_key()
        if subject_key:
            self._set_capture_state("measurement_ready")


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

    context_work_item_id = _ctx.get_work_item_id()
    explicit_work_item = bool(work_item_id or (_ctx.has_explicit_work_item() and context_work_item_id))
    wid = work_item_id or context_work_item_id or str(uuid.uuid4())
    eff_agent_id = agent_id or _ctx.get_agent_id() or config.agent_id
    eff_domain = domain or _ctx.get_domain() or config.domain
    eff_workflow_type = workflow_type or _ctx.get_workflow_type()
    eff_business_unit = business_unit or _ctx.get_business_unit()
    subject_key = _ctx.get_subject_key()
    readiness = "provisional"
    if explicit_work_item and eff_workflow_type and eff_agent_id:
        readiness = "attribution_ready"

    tracer = _tracer.get_tracer()
    with tracer.start_as_current_span("agent.run") as otel_span:
        otel_span.set_attribute("juvera.agent_id", eff_agent_id)
        otel_span.set_attribute("juvera.work_item_id", wid)
        otel_span.set_attribute("juvera.work_item_auto_generated", not explicit_work_item)
        otel_span.set_attribute("juvera.capture_source", "sdk")
        otel_span.set_attribute("juvera.instrumentation_readiness", readiness)
        otel_span.set_attribute("juvera.provisional", readiness == "provisional")
        if eff_domain:
            otel_span.set_attribute("juvera.domain", eff_domain)
        if eff_workflow_type:
            otel_span.set_attribute("juvera.workflow_type", eff_workflow_type)
        if eff_business_unit:
            otel_span.set_attribute("juvera.business_unit", eff_business_unit)
        if subject_key:
            otel_span.set_attribute("juvera.properties.subject_key", subject_key)
        user_id = _ctx.get_user_id()
        if user_id:
            otel_span.set_attribute("juvera.user_id", user_id)
        session_id = _ctx.get_session_id()
        if session_id:
            otel_span.set_attribute("juvera.session_id", session_id)
        metadata = _ctx.get_context_metadata()
        if metadata:
            otel_span.set_attribute("juvera.context.metadata_json", json.dumps(metadata, sort_keys=True))
        tags = _ctx.get_context_tags()
        if tags:
            otel_span.set_attribute("juvera.context.tags_json", json.dumps(tags))

        wid_token = _ctx._work_item_id.set(wid)
        wid_explicit_token = _ctx._work_item_explicit.set(explicit_work_item)
        aid_token = _ctx._agent_id.set(eff_agent_id)
        wf_token = _ctx._workflow_type.set(eff_workflow_type)
        juvera_span = AgentSpan(otel_span, wid)
        span_token = _ctx.set_current_span(juvera_span)
        try:
            yield juvera_span
        finally:
            _ctx._current_span.set(None)
            _ctx._work_item_id.reset(wid_token)
            _ctx._work_item_explicit.reset(wid_explicit_token)
            _ctx._agent_id.reset(aid_token)
            _ctx._workflow_type.reset(wf_token)
