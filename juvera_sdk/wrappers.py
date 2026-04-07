"""Developer-friendly client wrappers for raw provider SDKs."""
from __future__ import annotations

import importlib
import inspect
import time
from typing import Any, Callable

from juvera_sdk.decorators import _coerce_text, _parse_response, _read
from juvera_sdk.span import agent_span

_ctx = importlib.import_module("juvera_sdk.context")


def _resolve_agent_id(explicit_agent_id: str | None) -> str:
    if explicit_agent_id:
        return explicit_agent_id
    active_agent_id = _ctx.get_agent_id()
    if active_agent_id:
        return active_agent_id
    from juvera_sdk import _get_config

    config = _get_config()
    return config.agent_id or "juvera_agent"


def _extract_openai_prompt(kwargs: dict[str, Any]) -> str | None:
    if kwargs.get("messages") is not None:
        parts = []
        for message in kwargs.get("messages") or []:
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            text = _coerce_text(content)
            if text:
                parts.append(text)
        prompt = "\n".join(parts).strip()
        return prompt or None
    if kwargs.get("input") is not None:
        return _coerce_text(kwargs.get("input"))
    if kwargs.get("prompt") is not None:
        return _coerce_text(kwargs.get("prompt"))
    return None


def _extract_anthropic_prompt(kwargs: dict[str, Any]) -> str | None:
    parts = []
    for message in kwargs.get("messages") or []:
        if not isinstance(message, dict):
            continue
        text = _coerce_text(message.get("content"))
        if text:
            parts.append(text)
    prompt = "\n".join(parts).strip()
    return prompt or None


def _add_response_tool_calls(span: Any, *, provider: str, response: Any) -> None:
    if provider == "openai":
        choices = _read(response, "choices") or []
        if not choices:
            return
        message = _read(choices[0], "message")
        for tool_call in _read(message, "tool_calls") or []:
            name = _read(_read(tool_call, "function"), "name")
            if name:
                span.add_tool_call(str(name), status="success")
        return
    if provider == "anthropic":
        for block in _read(response, "content") or []:
            block_type = _read(block, "type")
            if block_type == "tool_use":
                name = _read(block, "name")
                if name:
                    span.add_tool_call(str(name), status="success")


def _apply_response_to_span(
    span: Any,
    response: Any,
    *,
    provider: str,
    parser: str,
    model_hint: str | None,
    latency_ms: int,
) -> None:
    parsed = _parse_response(response, parser)
    model = model_hint or parsed.get("model")
    provider_name = parsed.get("provider") or provider
    if model:
        span.set_model(str(model), provider=str(provider_name))
    completion = parsed.get("completion")
    if completion is not None:
        span.set_completion(str(completion))
    input_tokens = parsed.get("input_tokens")
    output_tokens = parsed.get("output_tokens")
    cache_read = parsed.get("cache_read_tokens")
    cache_creation = parsed.get("cache_creation_tokens")
    reasoning = parsed.get("reasoning_tokens")
    if input_tokens or output_tokens:
        span.set_tokens(
            input=int(input_tokens or 0),
            output=int(output_tokens or 0),
            cache_read=int(cache_read or 0),
            cache_creation=int(cache_creation or 0),
            reasoning=int(reasoning or 0),
        )
        # PROPAGATION: also set tokens on the current OTel span if different
        # This ensures manually-created parent spans capture the data
        try:
            from opentelemetry import trace as _otel_trace
            current = _otel_trace.get_current_span()
            wrapper_span = getattr(span, '_span', None)
            if current is not None and current is not wrapper_span and current.is_recording():
                current.set_attribute("gen_ai.usage.input_tokens", int(input_tokens or 0))
                current.set_attribute("gen_ai.usage.output_tokens", int(output_tokens or 0))
                if cache_read:
                    current.set_attribute("gen_ai.usage.cache_read_tokens", int(cache_read))
                if cache_creation:
                    current.set_attribute("gen_ai.usage.cache_creation_tokens", int(cache_creation))
                if reasoning:
                    current.set_attribute("gen_ai.usage.reasoning_tokens", int(reasoning))
                if model:
                    current.set_attribute("gen_ai.request.model", str(model))
                    current.set_attribute("gen_ai.system", str(provider_name))
        except Exception:
            pass
    span.set_attribute("juvera.latency_ms", latency_ms)
    _add_response_tool_calls(span, provider=provider, response=response)


def _call_with_optional_span(
    call: Callable[[], Any],
    *,
    provider: str,
    parser: str,
    prompt: str | None,
    model_hint: str | None,
    agent_id: str | None,
    default_workflow_type: str | None,
    domain: str | None,
    business_unit: str | None,
) -> Any:
    active_span = _ctx.get_current_span()
    if active_span is None:
        context_manager = agent_span(
            agent_id=_resolve_agent_id(agent_id),
            domain=domain,
            workflow_type=default_workflow_type,
            business_unit=business_unit,
        )
        active_span = context_manager.__enter__()
    else:
        context_manager = None

    if prompt:
        active_span.set_prompt(prompt)

    started = time.perf_counter()
    try:
        result = call()
    except Exception as exc:
        active_span.set_error(exc)
        if context_manager is not None:
            context_manager.__exit__(type(exc), exc, exc.__traceback__)
        raise

    if inspect.isawaitable(result):
        async def _await_result():
            try:
                response = await result
            except Exception as exc:
                active_span.set_error(exc)
                raise
            else:
                latency_ms = int((time.perf_counter() - started) * 1000)
                _apply_response_to_span(
                    active_span,
                    response,
                    provider=provider,
                    parser=parser,
                    model_hint=model_hint,
                    latency_ms=latency_ms,
                )
                return response
            finally:
                if context_manager is not None:
                    context_manager.__exit__(None, None, None)

        return _await_result()

    latency_ms = int((time.perf_counter() - started) * 1000)
    try:
        _apply_response_to_span(
            active_span,
            result,
            provider=provider,
            parser=parser,
            model_hint=model_hint,
            latency_ms=latency_ms,
        )
        return result
    finally:
        if context_manager is not None:
            context_manager.__exit__(None, None, None)


class _OpenAIStreamWrapper:
    """Wraps an OpenAI stream iterator to capture final usage chunk."""

    def __init__(self, stream, span, context_manager, provider, parser, model_hint, latency_start):
        self._stream = stream
        self._span = span
        self._context_manager = context_manager
        self._provider = provider
        self._parser = parser
        self._model_hint = model_hint
        self._latency_start = latency_start
        self._final_usage = None
        self._model = None
        self._finalized = False

    def __iter__(self):
        return self

    def __next__(self):
        try:
            chunk = next(self._stream)
        except StopIteration:
            self._finalize()
            raise
        # Capture usage if present (final chunk)
        if hasattr(chunk, 'usage') and chunk.usage is not None:
            self._final_usage = chunk.usage
        if hasattr(chunk, 'model') and chunk.model:
            self._model = chunk.model
        return chunk

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            chunk = await self._stream.__anext__()
        except StopAsyncIteration:
            self._finalize()
            raise
        if hasattr(chunk, 'usage') and chunk.usage is not None:
            self._final_usage = chunk.usage
        if hasattr(chunk, 'model') and chunk.model:
            self._model = chunk.model
        return chunk

    def _finalize(self):
        if self._finalized:
            return
        self._finalized = True
        if self._final_usage is not None:
            # Build a synthetic response with usage
            synthetic = type('Response', (), {
                'usage': self._final_usage,
                'model': self._model,
                'choices': [],
                'output_text': None,
            })()
            latency_ms = int((time.perf_counter() - self._latency_start) * 1000)
            try:
                _apply_response_to_span(
                    self._span, synthetic,
                    provider=self._provider, parser=self._parser,
                    model_hint=self._model_hint, latency_ms=latency_ms,
                )
            except Exception:
                pass
        if self._context_manager is not None:
            try:
                self._context_manager.__exit__(None, None, None)
            except Exception:
                pass

    def __getattr__(self, name):
        return getattr(self._stream, name)


class _AnthropicStreamWrapper:
    """Wraps an Anthropic stream iterator to aggregate token usage."""

    def __init__(self, stream, span, context_manager, model_hint, latency_start):
        self._stream = stream
        self._span = span
        self._context_manager = context_manager
        self._model_hint = model_hint
        self._latency_start = latency_start
        self._input_tokens = 0
        self._output_tokens = 0
        self._cache_creation = 0
        self._cache_read = 0
        self._model = None
        self._finalized = False

    def __iter__(self):
        return self

    def __next__(self):
        try:
            event = next(self._stream)
        except StopIteration:
            self._finalize()
            raise
        self._handle_event(event)
        return event

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            event = await self._stream.__anext__()
        except StopAsyncIteration:
            self._finalize()
            raise
        self._handle_event(event)
        return event

    def _handle_event(self, event):
        # Anthropic emits typed events
        event_type = getattr(event, 'type', None)
        if event_type == 'message_start':
            message = getattr(event, 'message', None)
            if message:
                usage = getattr(message, 'usage', None)
                if usage:
                    self._input_tokens = getattr(usage, 'input_tokens', 0) or 0
                    self._cache_creation = getattr(usage, 'cache_creation_input_tokens', 0) or 0
                    self._cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0
                self._model = getattr(message, 'model', None)
        elif event_type == 'message_delta':
            usage = getattr(event, 'usage', None)
            if usage:
                # Anthropic's message_delta usage.output_tokens is cumulative
                self._output_tokens = getattr(usage, 'output_tokens', self._output_tokens) or self._output_tokens

    def _finalize(self):
        if self._finalized:
            return
        self._finalized = True
        if self._input_tokens or self._output_tokens:
            try:
                if self._model:
                    self._span.set_model(str(self._model), provider='anthropic')
                self._span.set_tokens(
                    input=int(self._input_tokens),
                    output=int(self._output_tokens),
                    cache_read=int(self._cache_read),
                    cache_creation=int(self._cache_creation),
                )
                latency_ms = int((time.perf_counter() - self._latency_start) * 1000)
                self._span.set_attribute("juvera.latency_ms", latency_ms)
            except Exception:
                pass
        if self._context_manager is not None:
            try:
                self._context_manager.__exit__(None, None, None)
            except Exception:
                pass

    def __getattr__(self, name):
        return getattr(self._stream, name)


class _OpenAICompletionsProxy:
    def __init__(
        self,
        original_completions: Any,
        *,
        agent_id: str | None,
        default_workflow_type: str | None,
        domain: str | None,
        business_unit: str | None,
    ):
        self._original = original_completions
        self._agent_id = agent_id
        self._default_workflow_type = default_workflow_type
        self._domain = domain
        self._business_unit = business_unit

    def create(self, *args: Any, **kwargs: Any) -> Any:
        is_stream = kwargs.get("stream", False)
        if is_stream:
            # Inject include_usage into stream_options (preserving any existing options)
            stream_opts = dict(kwargs.get("stream_options") or {})
            stream_opts["include_usage"] = True
            kwargs["stream_options"] = stream_opts
            return self._handle_stream(*args, **kwargs)
        return _call_with_optional_span(
            lambda: self._original.create(*args, **kwargs),
            provider="openai",
            parser="openai",
            prompt=_extract_openai_prompt(kwargs),
            model_hint=kwargs.get("model"),
            agent_id=self._agent_id,
            default_workflow_type=self._default_workflow_type,
            domain=self._domain,
            business_unit=self._business_unit,
        )

    def _handle_stream(self, *args: Any, **kwargs: Any) -> Any:
        active_span = _ctx.get_current_span()
        if active_span is None:
            context_manager = agent_span(
                agent_id=_resolve_agent_id(self._agent_id),
                domain=self._domain,
                workflow_type=self._default_workflow_type,
                business_unit=self._business_unit,
            )
            active_span = context_manager.__enter__()
        else:
            context_manager = None
        prompt = _extract_openai_prompt(kwargs)
        if prompt:
            active_span.set_prompt(prompt)
        started = time.perf_counter()
        try:
            stream = self._original.create(*args, **kwargs)
        except Exception as exc:
            active_span.set_error(exc)
            if context_manager is not None:
                context_manager.__exit__(type(exc), exc, exc.__traceback__)
            raise
        return _OpenAIStreamWrapper(
            stream, active_span, context_manager,
            provider="openai", parser="openai",
            model_hint=kwargs.get("model"), latency_start=started,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original, name)


class _OpenAIResponsesProxy(_OpenAICompletionsProxy):
    pass


class _OpenAIChatProxy:
    def __init__(
        self,
        original_chat: Any,
        *,
        agent_id: str | None,
        default_workflow_type: str | None,
        domain: str | None,
        business_unit: str | None,
    ):
        self._original = original_chat
        self.completions = _OpenAICompletionsProxy(
            original_chat.completions,
            agent_id=agent_id,
            default_workflow_type=default_workflow_type,
            domain=domain,
            business_unit=business_unit,
        )

    def __getattr__(self, name: str) -> Any:
        if name == "completions":
            return self.completions
        return getattr(self._original, name)


class _AnthropicMessagesProxy:
    def __init__(
        self,
        original_messages: Any,
        *,
        agent_id: str | None,
        default_workflow_type: str | None,
        domain: str | None,
        business_unit: str | None,
    ):
        self._original = original_messages
        self._agent_id = agent_id
        self._default_workflow_type = default_workflow_type
        self._domain = domain
        self._business_unit = business_unit

    def create(self, *args: Any, **kwargs: Any) -> Any:
        is_stream = kwargs.get("stream", False)
        if is_stream:
            return self._handle_stream(*args, **kwargs)
        return _call_with_optional_span(
            lambda: self._original.create(*args, **kwargs),
            provider="anthropic",
            parser="anthropic",
            prompt=_extract_anthropic_prompt(kwargs),
            model_hint=kwargs.get("model"),
            agent_id=self._agent_id,
            default_workflow_type=self._default_workflow_type,
            domain=self._domain,
            business_unit=self._business_unit,
        )

    def _handle_stream(self, *args: Any, **kwargs: Any) -> Any:
        active_span = _ctx.get_current_span()
        if active_span is None:
            context_manager = agent_span(
                agent_id=_resolve_agent_id(self._agent_id),
                domain=self._domain,
                workflow_type=self._default_workflow_type,
                business_unit=self._business_unit,
            )
            active_span = context_manager.__enter__()
        else:
            context_manager = None
        prompt = _extract_anthropic_prompt(kwargs)
        if prompt:
            active_span.set_prompt(prompt)
        started = time.perf_counter()
        try:
            stream = self._original.create(*args, **kwargs)
        except Exception as exc:
            active_span.set_error(exc)
            if context_manager is not None:
                context_manager.__exit__(type(exc), exc, exc.__traceback__)
            raise
        return _AnthropicStreamWrapper(
            stream, active_span, context_manager,
            model_hint=kwargs.get("model"), latency_start=started,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original, name)


def wrap_openai(
    client: Any,
    *,
    agent_id: str | None = None,
    default_workflow_type: str | None = None,
    domain: str | None = None,
    business_unit: str | None = None,
) -> Any:
    """Wrap an OpenAI client so create() calls emit Juvera spans automatically."""

    if hasattr(client, "chat") and hasattr(client.chat, "completions"):
        client.chat = _OpenAIChatProxy(
            client.chat,
            agent_id=agent_id,
            default_workflow_type=default_workflow_type,
            domain=domain,
            business_unit=business_unit,
        )
    if hasattr(client, "responses"):
        client.responses = _OpenAIResponsesProxy(
            client.responses,
            agent_id=agent_id,
            default_workflow_type=default_workflow_type,
            domain=domain,
            business_unit=business_unit,
        )
    return client


def wrap_openai_responses(
    client: Any,
    *,
    agent_id: str | None = None,
    default_workflow_type: str | None = None,
    domain: str | None = None,
    business_unit: str | None = None,
) -> Any:
    """Wrap only the OpenAI Responses API surface."""

    if hasattr(client, "responses"):
        client.responses = _OpenAIResponsesProxy(
            client.responses,
            agent_id=agent_id,
            default_workflow_type=default_workflow_type,
            domain=domain,
            business_unit=business_unit,
        )
    return client


def wrap_anthropic(
    client: Any,
    *,
    agent_id: str | None = None,
    default_workflow_type: str | None = None,
    domain: str | None = None,
    business_unit: str | None = None,
) -> Any:
    """Wrap an Anthropic client so messages.create() emits Juvera spans automatically."""

    if hasattr(client, "messages"):
        client.messages = _AnthropicMessagesProxy(
            client.messages,
            agent_id=agent_id,
            default_workflow_type=default_workflow_type,
            domain=domain,
            business_unit=business_unit,
        )
    return client
