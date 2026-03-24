# juvera_sdk/roi.py
from __future__ import annotations
import warnings
from typing import Any


WORKFLOW_BASELINES: dict[str, dict[str, float]] = {
    "ticket_deflection":  {"human_cost_usd": 22.0,  "human_time_minutes": 15},
    "lead_qualification": {"human_cost_usd": 35.0,  "human_time_minutes": 25},
    "document_review":    {"human_cost_usd": 75.0,  "human_time_minutes": 45},
    "data_extraction":    {"human_cost_usd": 18.0,  "human_time_minutes": 12},
    "code_review":        {"human_cost_usd": 95.0,  "human_time_minutes": 30},
    "compliance_check":   {"human_cost_usd": 120.0, "human_time_minutes": 60},
    "content_generation": {"human_cost_usd": 50.0,  "human_time_minutes": 30},
}


def estimate_roi(
    workflow_type: str | None = None,
    agent_cost_usd: float | None = None,
) -> dict[str, Any] | None:
    """Estimate ROI using workflow baselines.

    Reads workflow_type from ContextVar if not passed explicitly.
    Returns None with a warning if workflow_type is unknown.
    """
    from juvera_sdk import _get_config
    from juvera_sdk import context as _ctx

    config = _get_config()

    eff_workflow_type = workflow_type or _ctx.get_workflow_type()

    if eff_workflow_type is None:
        warnings.warn(
            "estimate_roi() could not determine workflow_type. "
            "Pass workflow_type explicitly or set it via agent_span() or set_work_item().",
            stacklevel=2,
        )
        return None

    baselines = dict(WORKFLOW_BASELINES)
    if config.workflow_baselines:
        baselines.update(config.workflow_baselines)

    baseline = baselines.get(eff_workflow_type)
    if baseline is None:
        warnings.warn(
            f"No baseline found for workflow_type={eff_workflow_type!r}. "
            f"Known types: {list(baselines.keys())}. "
            f"Pass custom baselines via init(workflow_baselines={{...}}).",
            stacklevel=2,
        )
        return None

    baseline_cost = baseline["human_cost_usd"]
    baseline_time = baseline["human_time_minutes"]
    cost = agent_cost_usd if agent_cost_usd is not None else 0.0
    savings = baseline_cost - cost
    time_saved = baseline_time * (savings / baseline_cost) if baseline_cost > 0 else 0.0

    return {
        "estimated_savings_usd": round(savings, 2),
        "baseline_cost_usd": baseline_cost,
        "agent_cost_usd": round(cost, 4),
        "time_saved_minutes": round(time_saved, 1),
        "workflow_type": eff_workflow_type,
    }
