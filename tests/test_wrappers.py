from __future__ import annotations

import juvera_sdk as j
import pytest


class _OpenAIUsage:
    prompt_tokens = 42
    completion_tokens = 9


class _OpenAIFunction:
    name = "lookup_policy"


class _OpenAIToolCall:
    function = _OpenAIFunction()


class _OpenAIMessage:
    content = "Refund approved."
    tool_calls = [_OpenAIToolCall()]


class _OpenAIChoice:
    message = _OpenAIMessage()


class _OpenAIResponse:
    model = "gpt-4o-mini"
    usage = _OpenAIUsage()
    choices = [_OpenAIChoice()]


class _OpenAICompletions:
    def create(self, **kwargs):
        return _OpenAIResponse()


class _OpenAIChat:
    completions = _OpenAICompletions()


class _OpenAIClient:
    chat = _OpenAIChat()


class _AnthropicUsage:
    input_tokens = 33
    output_tokens = 12


class _AnthropicBlock:
    def __init__(self, text: str, block_type: str = "text", name: str | None = None):
        self.text = text
        self.type = block_type
        self.name = name


class _AnthropicResponse:
    model = "claude-sonnet-4-20250514"
    usage = _AnthropicUsage()
    content = [_AnthropicBlock("Escalate to billing."), _AnthropicBlock("", block_type="tool_use", name="lookup_crm")]


class _AnthropicMessages:
    def create(self, **kwargs):
        return _AnthropicResponse()


class _AnthropicClient:
    messages = _AnthropicMessages()


@pytest.fixture(autouse=True)
def sdk_init(mock_exporter):
    j.init(api_key="jvr_test", org_id="org_test", endpoint="local", _exporter=mock_exporter)
    yield mock_exporter
    j.shutdown()


def test_wrap_openai_creates_span_from_workflow_context(sdk_init):
    exporter = sdk_init
    client = j.wrap_openai(
        _OpenAIClient(),
        agent_id="support_agent",
        default_workflow_type="ticket_deflection",
    )

    with j.context(user_id="u_123", session_id="sess_abc", subject_key="customer_42"):
        with j.workflow(work_item_id="wi_123", workflow_type="ticket_deflection"):
            client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Can I get a refund?"}],
            )

    span = exporter.last_span()
    attrs = span.attributes
    assert attrs["juvera.agent_id"] == "support_agent"
    assert attrs["juvera.work_item_id"] == "wi_123"
    assert attrs["juvera.workflow_type"] == "ticket_deflection"
    assert attrs["juvera.user_id"] == "u_123"
    assert attrs["juvera.session_id"] == "sess_abc"
    assert attrs["juvera.properties.subject_key"] == "customer_42"
    assert attrs["gen_ai.prompt"] == "Can I get a refund?"
    assert attrs["gen_ai.request.model"] == "gpt-4o-mini"
    assert attrs["gen_ai.usage.input_tokens"] == 42
    assert attrs["gen_ai.usage.output_tokens"] == 9
    assert attrs["juvera.instrumentation_readiness"] == "attribution_ready"
    assert span.events[0].attributes["tool.name"] == "lookup_policy"


def test_wrap_anthropic_reuses_existing_agent_span(sdk_init):
    exporter = sdk_init
    client = j.wrap_anthropic(
        _AnthropicClient(),
        agent_id="support_agent",
        default_workflow_type="ticket_deflection",
    )

    with j.agent_span(agent_id="outer_agent", work_item_id="wi_outer", workflow_type="ticket_deflection"):
        client.messages.create(
            model="claude-sonnet-4-20250514",
            messages=[{"role": "user", "content": "Should I escalate this?"}],
        )

    assert exporter.span_count() == 1
    attrs = exporter.last_span().attributes
    assert attrs["juvera.agent_id"] == "outer_agent"
    assert attrs["juvera.work_item_id"] == "wi_outer"
    assert attrs["gen_ai.request.model"] == "claude-sonnet-4-20250514"
    assert attrs["gen_ai.system"] == "anthropic"
    assert attrs["gen_ai.usage.input_tokens"] == 33
    assert attrs["gen_ai.usage.output_tokens"] == 12
