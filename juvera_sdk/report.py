"""juvera report — aggregate captures, render HTML."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from jinja2 import Environment, FileSystemLoader, select_autoescape

from juvera_sdk._fmt import fmt_cost, fmt_savings, fmt_pct
from juvera_sdk.roi import WORKFLOW_BASELINES


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

    def _wf_key(e: dict[str, Any]) -> str:
        # Single normalization point: events with missing or None workflow_type
        # bucket as "unknown" in BOTH the aggregation pass below AND the
        # baseline metadata gather later. Without this, None-typed events get
        # bucketed via `or "unknown"` but excluded from the metadata pass
        # because `e.get("workflow_type") == "unknown"` is False for None.
        return e.get("workflow_type") or "unknown"

    # Aggregate by workflow type
    by_wf: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"runs": 0, "agent_cost": 0.0, "savings": 0.0, "attributed": 0}
    )
    for e in events:
        wf = _wf_key(e)
        row = by_wf[wf]
        row["runs"] += 1
        row["agent_cost"] += e.get("agent_cost_usd") or 0.0
        row["savings"] += e.get("estimated_savings_usd") or 0.0
        if e.get("work_item_id"):
            row["attributed"] += 1

    # Build workflow breakdown. Reads baseline metadata FROM events (so the
    # cross-process `juvera report` CLI attributes correctly without user
    # config). Mixed-source buckets suppress the badge — order-independent.
    # Legacy events (pre-hotfix Phase 1, no baseline_source field) fall back
    # to WORKFLOW_BASELINES with implicit source='default'. Edge case: pre-
    # hotfix demo.py events that ran with overrides applied would carry
    # override-derived savings but lack the metadata to flag it, so this
    # fallback could misattribute them. In practice `juvera demo` doesn't
    # persist events to disk, so the only persisted legacy events came from
    # local_relay which never saw overrides — making the fallback safe.
    by_workflow = []
    for wf, row in sorted(by_wf.items(), key=lambda kv: -kv[1]["savings"]):
        attribution_pct = (100.0 * row["attributed"] / row["runs"]) if row["runs"] else 0
        # Collect baseline metadata across ALL events for this workflow.
        wf_events = [e for e in events if _wf_key(e) == wf]
        sources_seen = set()
        urls_seen = set()
        confidences_seen = set()
        any_new_schema = False
        for e in wf_events:
            if "baseline_source" in e:
                any_new_schema = True
                sources_seen.add(e.get("baseline_source"))
                urls_seen.add(e.get("baseline_source_url"))
                confidences_seen.add(e.get("baseline_confidence"))
        # Badge renders only when EVERY event in the bucket agrees that it's
        # default-sourced with the same source_url + confidence.
        if any_new_schema:
            if sources_seen == {"default"} and len(urls_seen) == 1 and len(confidences_seen) == 1:
                confidence = next(iter(confidences_seen))
                source_url = next(iter(urls_seen))
            else:
                confidence = None
                source_url = None
        else:
            # Legacy event(s) — fall back to global. Safe because legacy
            # events came from local_relay which never saw user overrides.
            baseline = WORKFLOW_BASELINES.get(wf, {})
            confidence = baseline.get("confidence")
            source_url = baseline.get("source_url")
        by_workflow.append({
            "workflow_type": wf,
            "runs": row["runs"],
            "agent_cost": row["agent_cost"],
            "savings": row["savings"],
            "attribution_pct": attribution_pct,
            "agent_cost_fmt": fmt_cost(row["agent_cost"]),
            "savings_fmt": fmt_savings(row["savings"]),
            "attribution_pct_fmt": fmt_pct(attribution_pct, max_pct=100.0),
            "confidence": confidence,
            "source_url": source_url,
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
    recent = [
        {**r, "agent_cost_usd_fmt": fmt_cost(r.get("agent_cost_usd") or 0)}
        for r in recent
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window_label": window_label,
        "total_runs": total_runs,
        "total_savings": total_savings,
        "total_savings_fmt": fmt_savings(total_savings),
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
