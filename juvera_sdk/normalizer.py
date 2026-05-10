# juvera_sdk/normalizer.py
from __future__ import annotations
import importlib
import json
from typing import Any, TYPE_CHECKING

_ctx = importlib.import_module("juvera_sdk.context")

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import ReadableSpan

ATTRIBUTE_MAP: dict[str, str] = {
    # Phoenix conventions
    "input.value": "gen_ai.prompt",
    "output.value": "gen_ai.completion",
    "llm.token_count.prompt": "gen_ai.usage.input_tokens",
    "llm.token_count.completion": "gen_ai.usage.output_tokens",
    # Langfuse conventions
    "langfuse.input": "gen_ai.prompt",
    "langfuse.output": "gen_ai.completion",
    # Braintrust conventions
    "braintrust.input": "gen_ai.prompt",
    "braintrust.output": "gen_ai.completion",
    # AI production metrics used by Juvera's episode/judge surfaces.
    "gen_ai.response.duration_ms": "juvera.latency_ms",
    "llm.latency_ms": "juvera.latency_ms",
    "langfuse.latency_ms": "juvera.latency_ms",
    "braintrust.latency_ms": "juvera.latency_ms",
    "llm.context_window.limit_tokens": "juvera.context_window.limit_tokens",
    "llm.context_window.used_tokens": "juvera.context_window.used_tokens",
    "llm.context_window.truncated": "juvera.context_window.truncated",
    "llm.timeout": "juvera.timeout",
    "llm.prompt.malformed": "juvera.prompt.malformed",
}


def normalize_span_attributes(span: ReadableSpan) -> dict[str, Any] | None:
    """Return normalized attributes dict, or None if no normalization needed.

    Original attributes preserved. Mapped keys added only when
    the Juvera-canonical key is not already present.
    """
    attrs = dict(span.attributes or {})
    added = {}
    for source_key, target_key in ATTRIBUTE_MAP.items():
        if source_key in attrs and target_key not in attrs:
            added[target_key] = attrs[source_key]
    inherited = _build_inherited_context_attrs(attrs)
    for key, value in inherited.items():
        if key not in attrs:
            added[key] = value
    if not added:
        return None
    return {**attrs, **added}


def _build_inherited_context_attrs(attrs: dict[str, Any]) -> dict[str, Any]:
    inherited: dict[str, Any] = {}
    work_item_id = _ctx.get_work_item_id()
    if work_item_id:
        inherited["juvera.work_item_id"] = work_item_id
        inherited["juvera.work_item_auto_generated"] = not _ctx.has_explicit_work_item()
    workflow_type = _ctx.get_workflow_type()
    if workflow_type:
        inherited["juvera.workflow_type"] = workflow_type
    agent_id = _ctx.get_agent_id()
    if agent_id:
        inherited["juvera.agent_id"] = agent_id
    domain = _ctx.get_domain()
    if domain:
        inherited["juvera.domain"] = domain
    business_unit = _ctx.get_business_unit()
    if business_unit:
        inherited["juvera.business_unit"] = business_unit
    subject_key = _ctx.get_subject_key()
    if subject_key:
        inherited["juvera.properties.subject_key"] = subject_key
    user_id = _ctx.get_user_id()
    if user_id:
        inherited["juvera.user_id"] = user_id
    session_id = _ctx.get_session_id()
    if session_id:
        inherited["juvera.session_id"] = session_id
    metadata = _ctx.get_context_metadata()
    if metadata:
        inherited["juvera.context.metadata_json"] = json.dumps(metadata, sort_keys=True)
    tags = _ctx.get_context_tags()
    if tags:
        inherited["juvera.context.tags_json"] = json.dumps(tags)
    readiness = _infer_readiness(inherited | attrs)
    if readiness:
        inherited["juvera.capture_source"] = "sdk"
        inherited["juvera.instrumentation_readiness"] = readiness
        inherited["juvera.provisional"] = readiness == "provisional"
    return inherited


def _infer_readiness(attrs: dict[str, Any]) -> str | None:
    agent_id = bool(attrs.get("juvera.agent_id"))
    workflow_type = bool(attrs.get("juvera.workflow_type"))
    work_item_id = bool(attrs.get("juvera.work_item_id"))
    explicit_work_item = not bool(attrs.get("juvera.work_item_auto_generated"))
    subject_key = bool(attrs.get("juvera.properties.subject_key"))
    experiment_tag = bool(attrs.get("juvera.properties.experiment_id"))
    if agent_id and workflow_type and work_item_id and explicit_work_item:
        if subject_key and experiment_tag:
            return "measurement_ready"
        return "attribution_ready"
    if any([agent_id, workflow_type, work_item_id]):
        return "provisional"
    return None


class NormalizedSpan:
    """Lightweight wrapper overriding .attributes on an immutable ReadableSpan."""

    def __init__(self, span: ReadableSpan, normalized_attrs: dict[str, Any]):
        self._span = span
        self._normalized_attrs = normalized_attrs

    @property
    def attributes(self):
        return self._normalized_attrs

    def __getattr__(self, name):
        return getattr(self._span, name)
