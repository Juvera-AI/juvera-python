# tests/test_run_summary.py
import pytest
import juvera_sdk as j
from juvera_sdk.exporters.mock import MockExporter


@pytest.fixture(autouse=True)
def sdk_init(mock_exporter):
    j.init(api_key="jvr_test", org_id="org_test", endpoint="local",
           debug=True, _exporter=mock_exporter)
    yield mock_exporter
    j.shutdown()


def test_flush_prints_summary(sdk_init, capsys):
    with j.agent_span(agent_id="a1", work_item_id="wi_001",
                       workflow_type="ticket_deflection") as span:
        span.set_model("gpt-4o-mini", provider="openai")
        span.set_tokens(input=420, output=180)
        span.add_tool_call("lookup_crm")
    j.flush()
    out = capsys.readouterr().out
    assert "Juvera Run Summary" in out
    assert "Spans: 1" in out
    assert "Tools: 1" in out
    assert "gpt-4o-mini" in out
    assert "420 in / 180 out" in out


def test_summary_includes_roi(sdk_init, capsys):
    with j.agent_span(agent_id="a1", work_item_id="wi_001",
                       workflow_type="ticket_deflection") as span:
        span.set_model("gpt-4o-mini", provider="openai")
        span.set_tokens(input=420, output=180)
    j.flush()
    out = capsys.readouterr().out
    assert "ROI estimate" in out
    assert "$22.00 baseline" in out


def test_summary_counts_errors(sdk_init, capsys):
    with j.agent_span(agent_id="a1", work_item_id="wi_001") as span:
        span.set_error(ValueError("test error"))
    j.flush()
    out = capsys.readouterr().out
    assert "Errors: 1" in out


def test_summary_counts_handoffs(sdk_init, capsys):
    with j.agent_span(agent_id="a1", work_item_id="wi_001"):
        j.record_handoff(reason="escalation", reviewer_role="manager")
    j.flush()
    out = capsys.readouterr().out
    assert "Handoffs: 1" in out


def test_no_summary_in_production_mode(mock_exporter, capsys):
    j.init(api_key="jvr_test", org_id="org_test",
           endpoint="https://ingest.juvera.ai", _exporter=mock_exporter)
    with j.agent_span(agent_id="a1", work_item_id="wi_001"):
        pass
    j.flush()
    out = capsys.readouterr().out
    assert "Juvera Run Summary" not in out
    j.shutdown()
