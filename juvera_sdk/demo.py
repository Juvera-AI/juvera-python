"""juvera demo — synthetic agent run + ROI card renderer."""
from __future__ import annotations

import random
import warnings
from typing import Any

from juvera_sdk.costs import compute_token_cost_usd
from juvera_sdk.roi import WORKFLOW_BASELINES, estimate_roi


# Synthetic scenarios per workflow. Tuned so token counts are realistic for
# the workflow and the cost (catalog-derived) lands at sub-cent for cheap
# models — which is the actual ROI story.
_SCENARIOS: dict[str, dict[str, Any]] = {
    "ticket_deflection": {
        "agent_id": "support_agent",
        "model": "gpt-4o-mini",
        "provider": "openai",
        "input_tokens": 421,
        "output_tokens": 187,
        "duration_ms": 3200,
        "user_message": "Where's my refund for order #4291?",
        "tool_calls": [
            {"name": "lookup_order_status", "duration_ms": 45, "status": "success"},
            {"name": "lookup_refund_policy", "duration_ms": 38, "status": "success"},
        ],
    },
    "lead_qualification": {
        "agent_id": "sdr_agent",
        "model": "gpt-4o-mini",
        "provider": "openai",
        "input_tokens": 612,
        "output_tokens": 240,
        "duration_ms": 4500,
        "user_message": "Inbound from Acme Corp asking about pricing.",
        "tool_calls": [
            {"name": "lookup_crm_account", "duration_ms": 60, "status": "success"},
            {"name": "score_lead", "duration_ms": 50, "status": "success"},
        ],
    },
}


def generate_synthetic_run(
    workflow_type: str = "ticket_deflection",
    seed: int | None = None,
) -> dict[str, Any]:
    """Produce one synthetic agent-run dict suitable for write_capture_event()."""
    if workflow_type not in _SCENARIOS:
        if workflow_type not in WORKFLOW_BASELINES:
            warnings.warn(
                f"Unknown workflow_type={workflow_type!r}; "
                f"falling back to ticket_deflection.",
                stacklevel=2,
            )
        workflow_type = "ticket_deflection"
    rng = random.Random(seed)
    scenario = dict(_SCENARIOS[workflow_type])  # shallow copy
    cost = compute_token_cost_usd(
        scenario["model"], scenario["input_tokens"], scenario["output_tokens"],
        provider=scenario["provider"],
    )
    roi = estimate_roi(workflow_type, agent_cost_usd=cost) or {}
    run_id = "".join(rng.choices("0123456789ABCDEFGHJKMNPQRSTVWXYZ", k=26))
    return {
        "schema_version": "1",
        "event_id": run_id,
        "captured_at": "1970-01-01T00:00:00.000Z",  # overridden when written; tests use seed
        "source": "demo",
        "agent_id": scenario["agent_id"],
        "workflow_type": workflow_type,
        "work_item_id": None,
        "model": scenario["model"],
        "provider": scenario["provider"],
        "input_tokens": scenario["input_tokens"],
        "output_tokens": scenario["output_tokens"],
        "agent_cost_usd": cost,
        "duration_ms": scenario["duration_ms"],
        "status": "success",
        "tool_calls": scenario["tool_calls"],
        "error": None,
        "estimated_savings_usd": roi.get("estimated_savings_usd"),
        "_user_message": scenario["user_message"],  # for the card; not part of canonical schema
    }
