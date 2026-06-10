"""Regression suite for the post-PR-#203 review findings:
1. Display surfaces (demo, processor, report) must honor j.init() overrides.
2. Methodology badge must only render for default baselines (source == 'default').
3. Capture events must persist baseline metadata so the cross-process
   `juvera report` CLI attributes correctly.

All in-process tests use the endpoint='local' + try/finally: j.shutdown()
pattern mirrored from tests/test_estimate_roi_init_compat.py — so they
don't construct a cloud-pointing OTel exporter and don't leak _config
into later test modules.
"""
from __future__ import annotations

import juvera_sdk as j
from juvera_sdk.demo import generate_synthetic_run, render_roi_card


# ---------- In-process: demo.render_roi_card ----------

def test_demo_uses_override_cost_not_global():
    """Override ticket_deflection to $12; demo card must show $12.00, not $22.00."""
    j.init(
        api_key="jvr_test",
        org_id="org_test",
        endpoint="local",
        debug=True,
        workflow_baselines={
            "ticket_deflection": {"human_cost_usd": 12.0, "human_time_minutes": 8},
        },
    )
    try:
        run = generate_synthetic_run("ticket_deflection", seed=1)
        card = render_roi_card(run, color=False, unicode=False)
        assert "$12.00" in card, f"override cost not surfaced in demo card:\n{card}"
        assert "$22.00" not in card, f"default cost leaked despite override:\n{card}"
    finally:
        j.shutdown()


def test_demo_suppresses_methodology_badge_on_override():
    """Customer's overridden numbers aren't Juvera's to certify — no badge."""
    j.init(
        api_key="jvr_test",
        org_id="org_test",
        endpoint="local",
        debug=True,
        workflow_baselines={
            "ticket_deflection": {"human_cost_usd": 12.0, "human_time_minutes": 8},
        },
    )
    try:
        run = generate_synthetic_run("ticket_deflection", seed=1)
        card = render_roi_card(run, color=False, unicode=False)
        assert "Methodology:" not in card, (
            f"methodology badge rendered for overridden baseline (should suppress):\n{card}"
        )
    finally:
        j.shutdown()


def test_demo_renders_methodology_badge_for_default():
    """No override → default path → badge SHOULD render."""
    j.init(api_key="jvr_test", org_id="org_test", endpoint="local", debug=True)
    try:
        run = generate_synthetic_run("ticket_deflection", seed=1)
        card = render_roi_card(run, color=False, unicode=False)
        assert "Methodology:" in card, (
            f"methodology badge missing for default baseline (should render):\n{card}"
        )
        assert "juvera.ai/baselines#ticket_deflection" in card, (
            f"methodology URL missing for default baseline:\n{card}"
        )
    finally:
        j.shutdown()


def test_demo_override_for_one_workflow_does_not_affect_another():
    """Override lead_qualification; ticket_deflection still default-attributed."""
    j.init(
        api_key="jvr_test",
        org_id="org_test",
        endpoint="local",
        debug=True,
        workflow_baselines={
            "lead_qualification": {"human_cost_usd": 100.0, "human_time_minutes": 60},
        },
    )
    try:
        run = generate_synthetic_run("ticket_deflection", seed=1)
        card = render_roi_card(run, color=False, unicode=False)
        assert "$22.00" in card, f"default cost suppressed by unrelated override:\n{card}"
        assert "Methodology:" in card, (
            f"badge suppressed for default workflow under unrelated override:\n{card}"
        )
    finally:
        j.shutdown()


# ---------- In-process: processor.print_summary ----------
#
# Tests construct JuveraSpanProcessor directly with endpoint='local' (DebugExporter,
# no network), set _stats manually, and call print_summary(). j.init() establishes
# the _config that processor.print_summary reads via resolve_baseline.

def _processor_under_test():
    from juvera_sdk.processor import JuveraSpanProcessor
    proc = JuveraSpanProcessor(
        api_key="jvr_test", org_id="org_test", endpoint="local", debug=True,
    )
    proc._stats = {
        "span_count": 1,
        "tool_count": 0,
        "handoff_count": 0,
        "error_count": 0,
        "input_tokens": 500,   # >0 so _compute_cost > 0 and the ROI line renders
        "output_tokens": 200,
        "model": "gpt-4o-mini",
        "provider": "openai",
        "work_item_id": None,
        "workflow_type": "ticket_deflection",
        "pii_warnings": 0,
    }
    return proc


def test_processor_print_summary_uses_override_cost(capsys):
    """processor.print_summary's ROI estimate line must use the override cost."""
    j.init(
        api_key="jvr_test",
        org_id="org_test",
        endpoint="local",
        debug=True,
        workflow_baselines={
            "ticket_deflection": {"human_cost_usd": 12.0, "human_time_minutes": 8},
        },
    )
    try:
        proc = _processor_under_test()
        proc.print_summary()
        out = capsys.readouterr().out
        # Positively assert the ROI line rendered (don't rely on absence) AND
        # uses the override cost.
        assert "ROI estimate:" in out, f"ROI line missing — cost=0?:\n{out}"
        assert "$12.00 baseline" in out, f"override cost not surfaced:\n{out}"
        assert "$22.00 baseline" not in out, f"default cost leaked:\n{out}"
    finally:
        j.shutdown()


def test_processor_print_summary_suppresses_confidence_on_override(capsys):
    """processor.print_summary's confidence line must not render under override."""
    j.init(
        api_key="jvr_test",
        org_id="org_test",
        endpoint="local",
        debug=True,
        workflow_baselines={
            "ticket_deflection": {"human_cost_usd": 12.0, "human_time_minutes": 8},
        },
    )
    try:
        proc = _processor_under_test()
        proc.print_summary()
        out = capsys.readouterr().out
        # Confirm ROI line rendered (positive) AND confidence line did not.
        assert "ROI estimate:" in out, f"ROI line missing — cost=0?:\n{out}"
        assert "confidence:" not in out, (
            f"confidence line rendered under override (should suppress):\n{out}"
        )
    finally:
        j.shutdown()


def test_processor_print_summary_renders_badge_for_default(capsys):
    """No override → default path → confidence + URL line SHOULD render."""
    j.init(api_key="jvr_test", org_id="org_test", endpoint="local", debug=True)
    try:
        proc = _processor_under_test()
        proc.print_summary()
        out = capsys.readouterr().out
        assert "ROI estimate:" in out
        assert "confidence: medium" in out, f"confidence missing for default:\n{out}"
        assert "juvera.ai/baselines#ticket_deflection" in out, (
            f"methodology URL missing for default:\n{out}"
        )
    finally:
        j.shutdown()


# ---------- Event schema: demo.generate_synthetic_run persists baseline metadata ----------

def test_demo_event_persists_baseline_metadata_default():
    """For default workflows, event dict contains all 4 new baseline fields."""
    j.init(api_key="jvr_test", org_id="org_test", endpoint="local", debug=True)
    try:
        event = generate_synthetic_run("ticket_deflection", seed=1)
        assert event["baseline_cost_usd"] == 22.0
        assert event["baseline_source"] == "default"
        assert event["baseline_confidence"] == "medium"
        assert event["baseline_source_url"] == "https://juvera.ai/baselines#ticket_deflection"
    finally:
        j.shutdown()


def test_demo_event_marks_override_source():
    """For overridden workflows, event marks source='override' and nulls confidence/url."""
    j.init(
        api_key="jvr_test",
        org_id="org_test",
        endpoint="local",
        debug=True,
        workflow_baselines={
            "ticket_deflection": {"human_cost_usd": 12.0, "human_time_minutes": 8},
        },
    )
    try:
        event = generate_synthetic_run("ticket_deflection", seed=1)
        assert event["baseline_cost_usd"] == 12.0
        assert event["baseline_source"] == "override"
        assert event["baseline_confidence"] is None, (
            f"override must not carry default confidence: {event!r}"
        )
        assert event["baseline_source_url"] is None, (
            f"override must not carry default source_url: {event!r}"
        )
    finally:
        j.shutdown()


# ---------- Cross-process: report.build_report_context reads from event ----------
#
# These tests do NOT call j.init() — they simulate the actual `juvera report` CLI,
# which loads persisted events from disk in a separate process with no user config.

def test_report_renders_from_event_baseline_when_present():
    """Event with baseline_source='override' produces an em-dash row, no juvera link."""
    from juvera_sdk.report import render_html
    events = [{
        "captured_at": "2026-06-04T10:00:00Z",
        "workflow_type": "ticket_deflection",
        "agent_cost_usd": 0.001,
        "estimated_savings_usd": 11.99,
        "work_item_id": "wi_test",
        "agent_id": "a1",
        "status": "success",
        "baseline_cost_usd": 12.0,
        "baseline_source": "override",
        "baseline_confidence": None,
        "baseline_source_url": None,
    }]
    html = render_html(events, window_label="test")
    # Override → em-dash branch in template (existing {% else %}).
    # Check for the rendered <span> element specifically — the .provenance-na
    # class definition is in the template's CSS block on every render, so
    # `"provenance-na" in html` would be vacuously true regardless of branch.
    assert '<span class="provenance-na">&mdash;</span>' in html, (
        f"expected rendered em-dash span for override row, got HTML:\n{html[:2000]}"
    )
    # No methodology link to juvera.ai for the override row.
    assert "juvera.ai/baselines#ticket_deflection" not in html, (
        f"override row should not link to Juvera methodology page; HTML:\n{html[:2000]}"
    )


def test_report_falls_back_to_global_for_legacy_event():
    """Legacy event (pre-hotfix, no baseline_* fields) falls back to global."""
    from juvera_sdk.report import render_html
    events = [{
        "captured_at": "2026-06-04T10:00:00Z",
        "workflow_type": "ticket_deflection",
        "agent_cost_usd": 0.001,
        "estimated_savings_usd": 21.99,
        "work_item_id": "wi_legacy",
        "agent_id": "a1",
        "status": "success",
        # NO baseline_cost_usd / baseline_source / etc. — pre-hotfix event shape.
    }]
    html = render_html(events, window_label="test")
    # Fallback → default attribution → methodology link renders.
    assert "juvera.ai/baselines#ticket_deflection" in html, (
        f"legacy event should fall back to default and render methodology link; HTML:\n{html[:2000]}"
    )


def test_report_event_source_url_actually_read_from_event():
    """Regression: PROVES the event's baseline_source_url is honored (not just
    a fallback). Uses a workflow_type ABSENT from WORKFLOW_BASELINES, so a link
    can ONLY appear if report.py reads it from the event."""
    from juvera_sdk.report import render_html
    custom_url = "https://internal-docs.example.com/baselines/custom_ops"
    events = [{
        "captured_at": "2026-06-04T10:00:00Z",
        "workflow_type": "custom_ops",  # NOT in WORKFLOW_BASELINES
        "agent_cost_usd": 0.5,
        "estimated_savings_usd": 5.0,
        "work_item_id": "wi_custom",
        "agent_id": "a1",
        "status": "success",
        "baseline_cost_usd": 10.0,
        "baseline_source": "default",  # tag as default so badge renders
        "baseline_confidence": "high",
        "baseline_source_url": custom_url,
    }]
    html = render_html(events, window_label="test")
    assert custom_url in html, (
        f"event-supplied source_url must be read from the event when present "
        f"(workflow not in WORKFLOW_BASELINES so fallback can't produce this URL):\n{html[:2000]}"
    )


def test_report_splits_mixed_bucket_by_source():
    """Mixed default + override events for the same workflow must NOT silently
    pick first-event's attribution. The badge renders only when all events in
    the bucket agree on source='default' with the same source_url; otherwise
    the row suppresses the badge (em-dash). Order-independent."""
    from juvera_sdk.report import render_html
    base_event = {
        "captured_at": "2026-06-04T10:00:00Z",
        "workflow_type": "ticket_deflection",
        "agent_cost_usd": 0.001,
        "estimated_savings_usd": 1.0,
        "work_item_id": "wi",
        "agent_id": "a1",
        "status": "success",
    }
    default_event = {
        **base_event,
        "baseline_cost_usd": 22.0,
        "baseline_source": "default",
        "baseline_confidence": "medium",
        "baseline_source_url": "https://juvera.ai/baselines#ticket_deflection",
    }
    override_event = {
        **base_event,
        "baseline_cost_usd": 12.0,
        "baseline_source": "override",
        "baseline_confidence": None,
        "baseline_source_url": None,
    }
    # Default-first order
    html_a = render_html([default_event, override_event], window_label="test")
    assert "juvera.ai/baselines#ticket_deflection" not in html_a, (
        f"mixed bucket (default first) must suppress badge:\n{html_a[:2000]}"
    )
    # Override-first order — same outcome
    html_b = render_html([override_event, default_event], window_label="test")
    assert "juvera.ai/baselines#ticket_deflection" not in html_b, (
        f"mixed bucket (override first) must suppress badge:\n{html_b[:2000]}"
    )
