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


def test_agent_span_sets_ai_operational_metrics(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="agent_01", work_item_id="wi_metrics") as span:
        span.set_latency(812)
        span.set_context_window(used_tokens=4212, limit_tokens=128000, truncated=False, limit_exceeded=False)
        span.mark_malformed_prompt(True)
        span.mark_timeout(True)
        span.set_routing_decision("openai-primary")

    attrs = exporter.last_span().attributes
    assert attrs["juvera.latency_ms"] == 812
    assert attrs["gen_ai.response.duration_ms"] == 812
    assert attrs["juvera.context_window.used_tokens"] == 4212
    assert attrs["juvera.context_window.limit_tokens"] == 128000
    assert attrs["juvera.context_window.truncated"] is False
    assert attrs["juvera.context_window.limit_exceeded"] is False
    assert attrs["juvera.prompt.malformed"] is True
    assert attrs["juvera.timeout"] is True
    assert attrs["juvera.routing.decision"] == "openai-primary"


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


def test_agent_span_set_experiment_metadata(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="agent_01", work_item_id="wi_exp_001") as span:
        span.set_experiment(
            experiment_id="exp_support_routing_v3",
            variant_id="treatment",
            variant_label="Treatment",
            subject_key="acct_123",
            assignment_mode="external_tagging",
            exposure_event="agent.run",
            assignment_reason="router_decision",
            config_ref="prompt_v3",
            is_control=False,
        )

    attrs = exporter.last_span().attributes
    assert attrs["juvera.properties.experiment_id"] == "exp_support_routing_v3"
    assert attrs["juvera.properties.variant_id"] == "treatment"
    assert attrs["juvera.properties.variant_label"] == "Treatment"
    assert attrs["juvera.properties.subject_key"] == "acct_123"
    assert attrs["juvera.properties.assignment_mode"] == "external_tagging"
    assert attrs["juvera.properties.exposure_event"] == "agent.run"
    assert attrs["juvera.properties.is_control"] == "false"
