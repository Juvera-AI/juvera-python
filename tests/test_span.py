# tests/test_span.py
import pytest
import juvera_sdk as j
from juvera_sdk.exporters.mock import MockExporter


@pytest.fixture(autouse=True)
def sdk_init(mock_exporter):
    j.init(api_key="jvr_test", org_id="org_test", endpoint="local", _exporter=mock_exporter)
    yield mock_exporter
    j.shutdown()


def test_agent_span_stamps_required_attributes(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="agent_01", work_item_id="wi_001", workflow_type="ticket_deflection"):
        pass

    assert exporter.span_count() == 1
    attrs = exporter.last_span().attributes
    assert attrs["juvera.agent_id"] == "agent_01"
    assert attrs["juvera.work_item_id"] == "wi_001"
    assert attrs["juvera.workflow_type"] == "ticket_deflection"


def test_agent_span_set_model(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="agent_01", work_item_id="wi_002") as span:
        span.set_model("claude-sonnet-4-6", provider="anthropic")

    attrs = exporter.last_span().attributes
    assert attrs["gen_ai.request.model"] == "claude-sonnet-4-6"
    assert attrs["gen_ai.system"] == "anthropic"


def test_agent_span_set_tokens(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="agent_01", work_item_id="wi_003") as span:
        span.set_tokens(input=420, output=180)

    attrs = exporter.last_span().attributes
    assert attrs["gen_ai.usage.input_tokens"] == 420
    assert attrs["gen_ai.usage.output_tokens"] == 180


def test_agent_span_add_tool_call(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="agent_01", work_item_id="wi_004") as span:
        span.add_tool_call("lookup_crm", status="success")

    span = exporter.last_span()
    events = span.events
    assert len(events) == 1
    assert events[0].name == "tool.call"
    assert events[0].attributes["tool.name"] == "lookup_crm"


def test_agent_span_generates_work_item_id_if_omitted(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="agent_01"):
        pass

    attrs = exporter.last_span().attributes
    assert attrs.get("juvera.work_item_id") is not None
    assert len(attrs["juvera.work_item_id"]) > 8
