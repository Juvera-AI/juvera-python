# tests/test_prompt_completion.py
import pytest
import juvera_sdk as j
from juvera_sdk.exporters.mock import MockExporter


@pytest.fixture(autouse=True)
def sdk_init(mock_exporter):
    j.init(api_key="jvr_test", org_id="org_test", endpoint="local", _exporter=mock_exporter)
    yield mock_exporter
    j.shutdown()


def test_set_prompt(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="a1", work_item_id="wi_001") as span:
        span.set_prompt("What is the refund policy?")
    assert exporter.last_span().attributes["gen_ai.prompt"] == "What is the refund policy?"


def test_set_completion(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="a1", work_item_id="wi_001") as span:
        span.set_completion("Returns within 30 days.")
    assert exporter.last_span().attributes["gen_ai.completion"] == "Returns within 30 days."


def test_set_prompt_and_completion_together(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="a1", work_item_id="wi_001") as span:
        span.set_prompt("Hello")
        span.set_completion("Hi there")
    attrs = exporter.last_span().attributes
    assert attrs["gen_ai.prompt"] == "Hello"
    assert attrs["gen_ai.completion"] == "Hi there"


def test_add_context_source_minimal(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="a1", work_item_id="wi_001") as span:
        span.add_context_source("knowledge_base")
    events = exporter.last_span().events
    assert len(events) == 1
    assert events[0].name == "context.source"
    assert events[0].attributes["context.source.name"] == "knowledge_base"


def test_add_context_source_full(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="a1", work_item_id="wi_001") as span:
        span.add_context_source("policy_doc", doc_type="pdf", token_count=1200)
    event = exporter.last_span().events[0]
    assert event.attributes["context.source.doc_type"] == "pdf"
    assert event.attributes["context.source.token_count"] == 1200


def test_add_tool_call_with_duration(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="a1", work_item_id="wi_001") as span:
        span.add_tool_call("search_api", duration_ms=230)
    assert exporter.last_span().events[0].attributes["tool.duration_ms"] == 230


def test_add_tool_call_with_error(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="a1", work_item_id="wi_001") as span:
        span.add_tool_call("search_api", status="failure", error="timeout")
    event = exporter.last_span().events[0]
    assert event.attributes["tool.status"] == "failure"
    assert event.attributes["tool.error"] == "timeout"


def test_add_tool_call_backward_compat(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="a1", work_item_id="wi_001") as span:
        span.add_tool_call("lookup_crm", status="success")
    event = exporter.last_span().events[0]
    assert event.attributes["tool.name"] == "lookup_crm"
    assert "tool.duration_ms" not in dict(event.attributes)
    assert "tool.error" not in dict(event.attributes)
