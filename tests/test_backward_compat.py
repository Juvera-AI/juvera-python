"""Verify v0.1.4 API works identically after refactor."""
import pytest
import juvera_sdk as j
from juvera_sdk.exporters.mock import MockExporter


@pytest.fixture(autouse=True)
def sdk_init(mock_exporter):
    j.init(api_key="jvr_test", org_id="org_test", endpoint="local", _exporter=mock_exporter)
    yield mock_exporter
    j.shutdown()


def test_init_agent_span_basic(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="agent_01", work_item_id="wi_001") as span:
        span.set_model("gpt-4o-mini", provider="openai")
        span.set_tokens(input=420, output=180)
        span.add_tool_call("lookup_crm", status="success")
    assert exporter.span_count() >= 1
    attrs = exporter.last_span().attributes
    assert attrs["juvera.agent_id"] == "agent_01"
    assert attrs["juvera.work_item_id"] == "wi_001"
    assert attrs["gen_ai.request.model"] == "gpt-4o-mini"
    assert attrs["gen_ai.usage.input_tokens"] == 420


def test_record_handoff_inside_span(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="agent_99", work_item_id="wi_002"):
        j.record_handoff(reason="low_confidence", reviewer_role="tier2_support")
    spans = exporter.all_spans()
    handoff = next(s for s in spans if s.name == "agent.handoff")
    assert handoff.attributes["juvera.human_required"] is True
    assert handoff.attributes["juvera.agent_id"] == "agent_99"


def test_record_impact_signal_local_mode(sdk_init, capsys):
    with j.agent_span(agent_id="agent_01", work_item_id="wi_003"):
        j.record_impact_signal(
            impact_type="cost_reduction",
            value=18.5,
            impact_category="ticket_deflection",
            source_system="zendesk",
        )
    captured = capsys.readouterr()
    assert "IMPACT_SIGNAL" in captured.out


def test_flush_and_shutdown(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="agent_01", work_item_id="wi_004"):
        pass
    j.flush()
    assert exporter.span_count() >= 1


def test_version_attribute():
    assert hasattr(j, "__version__")


def test_all_exports():
    expected = {"init", "agent_span", "record_impact_signal",
                "record_handoff", "flush", "shutdown", "__version__",
                "set_work_item", "clear_work_item"}
    assert expected.issubset(set(j.__all__))
