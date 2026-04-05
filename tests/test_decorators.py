import pytest

import juvera_sdk as j


class _OpenAIUsage:
    prompt_tokens = 420
    completion_tokens = 180


class _OpenAIMessage:
    content = "Your refund has been approved."


class _OpenAIChoice:
    message = _OpenAIMessage()


class _OpenAIResponse:
    model = "gpt-4o-mini"
    usage = _OpenAIUsage()
    choices = [_OpenAIChoice()]


class _AnthropicUsage:
    input_tokens = 210
    output_tokens = 90


class _AnthropicBlock:
    def __init__(self, text: str):
        self.text = text


class _AnthropicResponse:
    model = "claude-sonnet-4-20250514"
    usage = _AnthropicUsage()
    content = [_AnthropicBlock("approved"), _AnthropicBlock(" with empathy")]


@pytest.fixture(autouse=True)
def sdk_init(mock_exporter):
    j.init(api_key="jvr_test", org_id="org_test", endpoint="local", _exporter=mock_exporter)
    yield mock_exporter
    j.shutdown()


def test_openai_decorator_extracts_span_fields_from_response(sdk_init):
    exporter = sdk_init

    @j.openai_agent(
        "resolution_agent",
        workflow_type="ticket_deflection",
        work_item_id="wi_{ticket.ticket_id}",
        prompt="prompt",
        tools=[j.tool_call("search_kb", duration_ms=120)],
    )
    def resolve(prompt, ticket, model="gpt-4o-mini"):
        return _OpenAIResponse()

    ticket = {"ticket_id": "ZD-123"}
    response = resolve("Draft a refund response", ticket)

    assert isinstance(response, _OpenAIResponse)
    span = exporter.last_span()
    attrs = span.attributes
    assert attrs["juvera.agent_id"] == "resolution_agent"
    assert attrs["juvera.work_item_id"] == "wi_ZD-123"
    assert attrs["juvera.workflow_type"] == "ticket_deflection"
    assert attrs["gen_ai.prompt"] == "Draft a refund response"
    assert attrs["gen_ai.request.model"] == "gpt-4o-mini"
    assert attrs["gen_ai.system"] == "openai"
    assert attrs["gen_ai.usage.input_tokens"] == 420
    assert attrs["gen_ai.usage.output_tokens"] == 180
    assert attrs["gen_ai.completion"] == "Your refund has been approved."

    tool_event = span.events[0]
    assert tool_event.name == "tool.call"
    assert tool_event.attributes["tool.name"] == "search_kb"
    assert tool_event.attributes["tool.duration_ms"] == 120


def test_anthropic_decorator_supports_callable_resolvers_and_response_text(sdk_init):
    exporter = sdk_init

    @j.anthropic_agent(
        "qa_agent",
        workflow_type="ticket_deflection",
        work_item_id=lambda ticket: f"wi_{ticket['ticket_id']}",
        prompt="prompt",
    )
    def review(prompt, ticket):
        return _AnthropicResponse()

    response = review("Review this support reply", {"ticket_id": "ZD-456"})

    assert j.response_text(response) == "approved\n with empathy"
    span = exporter.last_span()
    attrs = span.attributes
    assert attrs["juvera.agent_id"] == "qa_agent"
    assert attrs["juvera.work_item_id"] == "wi_ZD-456"
    assert attrs["gen_ai.request.model"] == "claude-sonnet-4-20250514"
    assert attrs["gen_ai.system"] == "anthropic"
    assert attrs["gen_ai.usage.input_tokens"] == 210
    assert attrs["gen_ai.usage.output_tokens"] == 90
    assert attrs["gen_ai.completion"] == "approved\n with empathy"


@pytest.mark.asyncio
async def test_instrument_decorator_supports_async_functions(sdk_init):
    exporter = sdk_init

    @j.instrument(
        "triage_agent",
        workflow_type="ticket_deflection",
        work_item_id="wi_{ticket_id}",
        prompt="prompt",
        response_parser="openai",
    )
    async def classify(prompt, ticket_id):
        return _OpenAIResponse()

    response = await classify("Classify this ticket", "ZD-789")

    assert isinstance(response, _OpenAIResponse)
    attrs = exporter.last_span().attributes
    assert attrs["juvera.work_item_id"] == "wi_ZD-789"
    assert attrs["gen_ai.prompt"] == "Classify this ticket"
