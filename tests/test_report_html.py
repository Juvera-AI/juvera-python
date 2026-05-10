from juvera_sdk.report import build_report_context, render_html


SAMPLE_EVENTS = [
    {"schema_version": "1", "event_id": "e1", "captured_at": "2026-05-08T10:00:00Z",
     "source": "demo", "agent_id": "support_agent", "workflow_type": "ticket_deflection",
     "work_item_id": None, "model": "gpt-4o-mini", "provider": "openai",
     "input_tokens": 421, "output_tokens": 187, "agent_cost_usd": 0.000175,
     "duration_ms": 3200, "status": "success", "tool_calls": [], "error": None,
     "estimated_savings_usd": 21.999825},
    {"schema_version": "1", "event_id": "e2", "captured_at": "2026-05-08T11:00:00Z",
     "source": "capture", "agent_id": "support_agent", "workflow_type": "ticket_deflection",
     "work_item_id": "wi_ZD123", "model": "gpt-4o-mini", "provider": "openai",
     "input_tokens": 500, "output_tokens": 200, "agent_cost_usd": 0.000195,
     "duration_ms": 3500, "status": "success", "tool_calls": [], "error": None,
     "estimated_savings_usd": 21.999805},
]


def test_build_report_context_aggregates_correctly():
    ctx = build_report_context(SAMPLE_EVENTS, window_label="last 30d")
    assert ctx["total_runs"] == 2
    assert abs(ctx["total_savings"] - 43.99963) < 0.001
    assert ctx["top_workflow"] == "ticket_deflection"
    assert ctx["unattributed_runs"] == 1


def test_render_html_contains_hero_and_sections():
    html = render_html(SAMPLE_EVENTS, window_label="last 30d")
    assert "Juvera ROI Report" in html
    assert "ticket_deflection" in html
    assert "+$43.99" in html  # floored, not rounded
    assert "Attribution gap" in html
    assert "Next steps" in html


def test_render_html_handles_empty_events():
    html = render_html([], window_label="last 7d")
    assert "0 agent runs captured" in html
    assert "last 7d" in html  # window_label rendered
    assert "+$0.00" in html


def test_render_html_escapes_user_controlled_fields():
    """Critical: agent_id and other user-controlled fields must be HTML-escaped."""
    hostile_event = {
        "schema_version": "1", "event_id": "e_xss", "captured_at": "2026-05-08T10:00:00Z",
        "source": "demo", "agent_id": "<script>alert('xss')</script>",
        "workflow_type": "ticket_deflection", "work_item_id": None,
        "model": "gpt-4o-mini", "provider": "openai",
        "input_tokens": 100, "output_tokens": 50, "agent_cost_usd": 0.0001,
        "duration_ms": 1000, "status": "success", "tool_calls": [], "error": None,
        "estimated_savings_usd": 21.99,
    }
    html = render_html([hostile_event], window_label="last 7d")
    assert "<script>alert" not in html, "XSS sink — autoescape not working"
    assert "&lt;script&gt;" in html, "Expected HTML-escaped script tag"
