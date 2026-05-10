"""juvera report — aggregate captures, render HTML."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from jinja2 import Environment, FileSystemLoader, select_autoescape


_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def filter_events(
    events: Iterable[dict[str, Any]],
    *,
    since_date: str | None = None,
    source: str | None = None,
) -> Iterable[dict[str, Any]]:
    """Filter events by date and/or source. Yields matching events."""
    for e in events:
        if since_date and e.get("captured_at", "") < since_date:
            continue
        if source and e.get("source") != source:
            continue
        yield e


def build_report_context(
    events: list[dict[str, Any]],
    *,
    window_label: str,
) -> dict[str, Any]:
    """Aggregate events into report context dict for Jinja2 rendering."""
    total_runs = len(events)
    total_savings = sum((e.get("estimated_savings_usd") or 0.0) for e in events)

    # Aggregate by workflow type
    by_wf: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"runs": 0, "agent_cost": 0.0, "savings": 0.0, "attributed": 0}
    )
    for e in events:
        wf = e.get("workflow_type") or "unknown"
        row = by_wf[wf]
        row["runs"] += 1
        row["agent_cost"] += e.get("agent_cost_usd") or 0.0
        row["savings"] += e.get("estimated_savings_usd") or 0.0
        if e.get("work_item_id"):
            row["attributed"] += 1

    # Build workflow breakdown
    by_workflow = []
    for wf, row in sorted(by_wf.items(), key=lambda kv: -kv[1]["savings"]):
        by_workflow.append({
            "workflow_type": wf,
            "runs": row["runs"],
            "agent_cost": row["agent_cost"],
            "savings": row["savings"],
            "attribution_pct": (100.0 * row["attributed"] / row["runs"]) if row["runs"] else 0,
        })

    top_workflow = by_workflow[0]["workflow_type"] if by_workflow else "—"
    unattributed_runs = sum(1 for e in events if not e.get("work_item_id"))

    # Extract top issues (errors and escalations)
    top_issues = [
        {
            "captured_at": e["captured_at"],
            "agent_id": e.get("agent_id", "?"),
            "issue": e.get("error") or "escalated",
        }
        for e in events
        if e.get("status") == "error" or e.get("status") == "escalated"
    ][:10]

    # Get recent runs (last 50, reverse chronological)
    recent = sorted(events, key=lambda e: e.get("captured_at", ""), reverse=True)[:50]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window_label": window_label,
        "total_runs": total_runs,
        "total_savings": total_savings,
        "top_workflow": top_workflow,
        "by_workflow": by_workflow,
        "top_issues": top_issues,
        "unattributed_runs": unattributed_runs,
        "recent": recent,
    }


def render_html(events: list[dict[str, Any]], *, window_label: str) -> str:
    """Render events into HTML report using Jinja2 template with autoescape enabled."""
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
    )
    template = env.get_template("report.html.j2")
    ctx = build_report_context(events, window_label=window_label)
    return template.render(**ctx)
