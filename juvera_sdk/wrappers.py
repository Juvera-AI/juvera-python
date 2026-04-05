"""Client wrappers for auto-instrumentation of OpenAI and Anthropic clients.

Usage:
    from openai import OpenAI
    import juvera_sdk as j

    client = j.wrap_openai(OpenAI())
    # All calls auto-captured: tokens, model, cost, latency
    response = client.chat.completions.create(...)
"""
from __future__ import annotations

import time
from typing import Any

from juvera_sdk import context as _ctx


class _OpenAICompletionsProxy:
    """Proxy for client.chat.completions that auto-instruments create()."""

    def __init__(self, original_completions: Any):
        self._original = original_completions

    def create(self, **kwargs: Any) -> Any:
        span = _ctx.get_current_span()
        model = kwargs.get("model", "")

        t0 = time.time()
        response = self._original.create(**kwargs)
        latency_ms = int((time.time() - t0) * 1000)

        if span is not None:
            span.set_model(model, provider="openai")
            if hasattr(response, "usage") and response.usage:
                span.set_tokens(
                    input=getattr(response.usage, "prompt_tokens", 0) or 0,
                    output=getattr(response.usage, "completion_tokens", 0) or 0,
                )
            # Extract completion text
            choices = getattr(response, "choices", None)
            if choices and len(choices) > 0:
                message = getattr(choices[0], "message", None)
                if message:
                    content = getattr(message, "content", None)
                    if content:
                        span.set_completion(str(content))
            span.set_attribute("juvera.latency_ms", latency_ms)

        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original, name)


class _OpenAIChatProxy:
    """Proxy for client.chat that wraps completions."""

    def __init__(self, original_chat: Any):
        self._original = original_chat
        self.completions = _OpenAICompletionsProxy(original_chat.completions)

    def __getattr__(self, name: str) -> Any:
        if name == "completions":
            return self.completions
        return getattr(self._original, name)


class _AnthropicMessagesProxy:
    """Proxy for client.messages that auto-instruments create()."""

    def __init__(self, original_messages: Any):
        self._original = original_messages

    def create(self, **kwargs: Any) -> Any:
        span = _ctx.get_current_span()
        model = kwargs.get("model", "")

        t0 = time.time()
        response = self._original.create(**kwargs)
        latency_ms = int((time.time() - t0) * 1000)

        if span is not None:
            span.set_model(model, provider="anthropic")
            if hasattr(response, "usage") and response.usage:
                span.set_tokens(
                    input=getattr(response.usage, "input_tokens", 0) or 0,
                    output=getattr(response.usage, "output_tokens", 0) or 0,
                )
            # Extract completion text
            content = getattr(response, "content", None)
            if content and isinstance(content, list) and len(content) > 0:
                text_block = content[0]
                text = getattr(text_block, "text", None)
                if text:
                    span.set_completion(str(text))
            span.set_attribute("juvera.latency_ms", latency_ms)

        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original, name)


def wrap_openai(client: Any) -> Any:
    """Wrap an OpenAI client for automatic instrumentation.

    Usage:
        from openai import OpenAI
        client = wrap_openai(OpenAI())
        # All chat.completions.create() calls auto-captured
    """
    client.chat = _OpenAIChatProxy(client.chat)
    return client


def wrap_anthropic(client: Any) -> Any:
    """Wrap an Anthropic client for automatic instrumentation.

    Usage:
        from anthropic import Anthropic
        client = wrap_anthropic(Anthropic())
        # All messages.create() calls auto-captured
    """
    client.messages = _AnthropicMessagesProxy(client.messages)
    return client
