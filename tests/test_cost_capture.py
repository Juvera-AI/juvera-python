"""Tests for cost capture — token extraction from provider responses."""
from juvera_sdk.decorators import _parse_openai_response, _parse_anthropic_response


class _MockUsage:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class _MockDetails:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class _MockChoice:
    def __init__(self, content):
        self.message = type('M', (), {'content': content, 'tool_calls': None})()

class _MockOpenAIResponse:
    def __init__(self, prompt_tokens=100, completion_tokens=50, cached_tokens=0, reasoning_tokens=0):
        self.model = "gpt-4o"
        self.choices = [_MockChoice("Hello")]
        self.output_text = None
        self.usage = _MockUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            prompt_tokens_details=_MockDetails(cached_tokens=cached_tokens),
            completion_tokens_details=_MockDetails(reasoning_tokens=reasoning_tokens),
        )

class _MockAnthropicResponse:
    def __init__(self, input_tokens=100, output_tokens=50, cache_creation=0, cache_read=0):
        self.model = "claude-sonnet-4-20250514"
        self.content = [type('B', (), {'type': 'text', 'text': 'Hello'})()]
        self.usage = _MockUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_input_tokens=cache_creation,
            cache_read_input_tokens=cache_read,
        )


def test_openai_extracts_base_tokens():
    parsed = _parse_openai_response(_MockOpenAIResponse())
    assert parsed["input_tokens"] == 100
    assert parsed["output_tokens"] == 50


def test_openai_extracts_cached_tokens():
    parsed = _parse_openai_response(_MockOpenAIResponse(cached_tokens=30))
    assert parsed["cache_read_tokens"] == 30


def test_openai_extracts_reasoning_tokens():
    parsed = _parse_openai_response(_MockOpenAIResponse(reasoning_tokens=20))
    assert parsed["reasoning_tokens"] == 20


def test_anthropic_extracts_base_tokens():
    parsed = _parse_anthropic_response(_MockAnthropicResponse())
    assert parsed["input_tokens"] == 100
    assert parsed["output_tokens"] == 50


def test_anthropic_extracts_cache_creation():
    parsed = _parse_anthropic_response(_MockAnthropicResponse(cache_creation=40))
    assert parsed["cache_creation_tokens"] == 40


def test_anthropic_extracts_cache_read():
    parsed = _parse_anthropic_response(_MockAnthropicResponse(cache_read=60))
    assert parsed["cache_read_tokens"] == 60


def test_openai_no_cache_returns_none():
    parsed = _parse_openai_response(_MockOpenAIResponse())
    assert parsed["cache_read_tokens"] is None or parsed["cache_read_tokens"] == 0


def test_anthropic_no_cache_returns_none():
    parsed = _parse_anthropic_response(_MockAnthropicResponse())
    assert parsed["cache_creation_tokens"] is None or parsed["cache_creation_tokens"] == 0
    assert parsed["cache_read_tokens"] is None or parsed["cache_read_tokens"] == 0
