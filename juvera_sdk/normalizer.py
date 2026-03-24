# juvera_sdk/normalizer.py
from __future__ import annotations
from typing import Any, TYPE_CHECKING

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
    if not added:
        return None
    return {**attrs, **added}


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
