"""juvera demo — synthetic agent run + ROI card renderer."""
from __future__ import annotations

import random
import re
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
        if workflow_type in WORKFLOW_BASELINES:
            warnings.warn(
                f"No synthetic scenario for workflow_type={workflow_type!r} yet; "
                f"falling back to ticket_deflection. (workflow exists in baselines but "
                f"a synthetic scenario hasn't been authored)",
                stacklevel=2,
            )
        else:
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


_GREEN = "\x1b[32m"
_DIM = "\x1b[2m"
_RESET = "\x1b[0m"


def _box_chars(unicode: bool) -> dict[str, str]:
    if unicode:
        return {"tl": "┌", "tr": "┐", "bl": "└", "br": "┘", "h": "─", "v": "│"}
    return {"tl": "+", "tr": "+", "bl": "+", "br": "+", "h": "-", "v": "|"}


def render_roi_card(
    run: dict[str, Any],
    *,
    color: bool = True,
    unicode: bool = True,
    width: int = 63,
) -> str:
    """Render the styled ROI card for a single synthetic or real agent run.

    `color` and `unicode` should be set by the caller based on TTY/locale detection
    (see `cli.py` for `_should_use_color()` / `_should_use_unicode()`).
    """
    box = _box_chars(unicode)
    arrow = "→" if unicode else "->"
    dot = "·" if unicode else "-"
    baseline = WORKFLOW_BASELINES.get(run["workflow_type"], {})
    baseline_cost = baseline.get("human_cost_usd", 0.0)
    baseline_time = baseline.get("human_time_minutes", 0)
    agent_cost = run["agent_cost_usd"]
    stored_savings = run.get("estimated_savings_usd")
    savings = stored_savings if stored_savings is not None else (baseline_cost - agent_cost)
    pct = (savings / baseline_cost * 100) if baseline_cost else 0.0
    time_saved = baseline_time * (savings / baseline_cost) if baseline_cost else 0.0

    saved_label = f"+${savings:.2f}  ({pct:.2f}% cost reduction)"
    if color:
        saved_label = f"{_GREEN}{saved_label}{_RESET}"
    next_line = "Next: add work_item_id to verify against real outcomes."
    if color:
        next_line = f"{_DIM}{next_line}{_RESET}"

    lines = [
        f"Simulating 1 {run['workflow_type'].replace('_', ' ')} run...",
        "",
        f'  {arrow} Agent received: "{run.get("_user_message", "")}"',
    ]
    for tc in run["tool_calls"]:
        lines.append(f"  {arrow} Tool call: {tc['name']:<24}({tc['duration_ms']}ms)")
    lines.append(f"  {arrow} Agent responded in {run['duration_ms'] / 1000:.1f}s")
    lines.append(
        f"  {arrow} Tokens: {run['input_tokens']} in / {run['output_tokens']} out {dot} "
        f"{run['model']} {dot} ${agent_cost:.2f}"
    )
    lines.append("")

    inner = width - 2

    def _row(text: str = "") -> str:
        # Strip ANSI for width calc; pad raw text to inner width.
        plain = re.sub(r"\x1b\[[0-9;]*m", "", text)
        pad = inner - len(plain)
        return f"{box['v']} {text}{' ' * (pad - 1)}{box['v']}"

    border_top = box["tl"] + box["h"] * inner + box["tr"]
    border_bot = box["bl"] + box["h"] * inner + box["br"]
    lines += [
        border_top,
        _row("Juvera captured 1 agent run"),
        _row(),
        _row(f"Workflow:        {run['workflow_type']}"),
        _row(f"Human baseline:  ${baseline_cost:.2f} {dot} {baseline_time} min"),
        _row(f"Agent cost:      ${agent_cost:.2f}"),
        _row(f"Estimated value: {saved_label}"),
        _row(f"Time saved:      {time_saved:.1f} min"),
        _row("Readiness:       provisional"),
        _row(),
        _row(next_line),
        border_bot,
        "",
        "  Full HTML report:       juvera report",
        f"  Instrument your code:   pip install juvera-sdk  {arrow}  README.md",
    ]
    return "\n".join(lines)
