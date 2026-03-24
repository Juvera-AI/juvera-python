# juvera_sdk/events.py
from __future__ import annotations
import warnings
from opentelemetry import trace


def record_event(
    event_type: str,
    properties: dict | None = None,
    status: str = "success",
) -> None:
    """Record a custom event on the current agent span.

    Must be called inside an agent_span() context manager.
    """
    span = trace.get_current_span()

    if not span.is_recording():
        warnings.warn(
            "record_event() called outside an active agent_span. "
            "The event will be silently dropped. "
            "Call record_event() inside a 'with agent_span(...)' block.",
            stacklevel=2,
        )
        return

    event_attrs: dict[str, str] = {"event.status": status}
    if properties:
        for k, v in properties.items():
            event_attrs[f"event.{k}"] = str(v)
    span.add_event(event_type, event_attrs)
