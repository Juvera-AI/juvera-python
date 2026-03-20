# juvera_sdk/handoff.py
from __future__ import annotations
import juvera_sdk.tracer as _tracer
from juvera_sdk import context as _ctx


def record_handoff(
    reason: str,
    reviewer_role: str,
    work_item_id: str | None = None,
) -> None:
    """Record a human-in-the-loop handoff as an OTel child span."""
    from juvera_sdk import _get_config
    config = _get_config()

    wid = work_item_id or _ctx.get_work_item_id()
    if wid is None:
        import warnings
        warnings.warn(
            "record_handoff() called outside an active agent_span with no work_item_id. "
            "The handoff span will be emitted on a new trace with no work_item context. "
            "Call record_handoff() inside a 'with agent_span(...)' block, or pass work_item_id explicitly.",
            stacklevel=2,
        )
    cost = config.human_reviewer_cost_per_hour_usd * (15 / 60)  # 15-min estimate

    tracer = _tracer.get_tracer()
    with tracer.start_as_current_span("agent.handoff") as span:
        span.set_attribute("juvera.human_required", True)
        span.set_attribute("juvera.handoff_reason", reason)
        span.set_attribute("juvera.reviewer_role", reviewer_role)
        span.set_attribute("juvera.supervision_cost_usd", cost)
        if wid:
            span.set_attribute("juvera.work_item_id", wid)
        aid = _ctx.get_agent_id()
        if aid:
            span.set_attribute("juvera.agent_id", aid)
