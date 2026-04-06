from __future__ import annotations

import inspect
import re
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable

from juvera_sdk.span import agent_span

_MISSING = object()
_TEMPLATE_PATTERN = re.compile(r"\{([^{}]+)\}")


@dataclass(frozen=True)
class ToolCallSpec:
    tool_name: str
    status: str = "success"
    duration_ms: int | None = None
    error: str | None = None


def tool_call(
    tool_name: str,
    *,
    status: str = "success",
    duration_ms: int | None = None,
    error: str | None = None,
) -> ToolCallSpec:
    """Describe a tool call for decorator-based instrumentation."""

    return ToolCallSpec(
        tool_name=tool_name,
        status=status,
        duration_ms=duration_ms,
        error=error,
    )


def instrument(
    agent_id: str,
    *,
    workflow_type: str | None = None,
    domain: str | None = None,
    business_unit: str | None = None,
    work_item_id: Any = None,
    prompt: Any = None,
    model: Any = None,
    provider: Any = None,
    tools: Any = None,
    response_parser: str | Callable[[Any], dict[str, Any] | None] | None = "auto",
):
    """Instrument a function call with a Juvera agent span.

    Resolver-like arguments (`work_item_id`, `prompt`, `model`, `provider`, `tools`)
    accept:
      - a constant value
      - an argument name such as `"prompt"`
      - a format string such as `"wi_{ticket.ticket_id}"`
      - a callable such as `lambda ticket: f"wi_{ticket['ticket_id']}"`
    """

    def decorator(func: Callable[..., Any]):
        signature = inspect.signature(func)

        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any):
                return await _invoke_instrumented(
                    func,
                    signature,
                    args,
                    kwargs,
                    agent_id=agent_id,
                    workflow_type=workflow_type,
                    domain=domain,
                    business_unit=business_unit,
                    work_item_id=work_item_id,
                    prompt=prompt,
                    model=model,
                    provider=provider,
                    tools=tools,
                    response_parser=response_parser,
                )

            return async_wrapper

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            return _invoke_instrumented_sync(
                func,
                signature,
                args,
                kwargs,
                agent_id=agent_id,
                workflow_type=workflow_type,
                domain=domain,
                business_unit=business_unit,
                work_item_id=work_item_id,
                prompt=prompt,
                model=model,
                provider=provider,
                tools=tools,
                response_parser=response_parser,
            )

        return wrapper

    return decorator


def openai_agent(
    agent_id: str,
    **kwargs: Any,
):
    """Decorator for OpenAI Chat/Responses-style calls."""

    kwargs.setdefault("response_parser", "openai")
    kwargs.setdefault("provider", "openai")
    return instrument(agent_id, **kwargs)


def anthropic_agent(
    agent_id: str,
    **kwargs: Any,
):
    """Decorator for Anthropic Messages API calls."""

    kwargs.setdefault("response_parser", "anthropic")
    kwargs.setdefault("provider", "anthropic")
    return instrument(agent_id, **kwargs)


def response_text(response: Any, parser: str = "auto") -> str | None:
    """Extract a human-readable text payload from a provider response."""

    parsed = _parse_response(response, parser)
    completion = parsed.get("completion")
    if completion is None:
        return None
    return str(completion)


async def _invoke_instrumented(
    func: Callable[..., Any],
    signature: inspect.Signature,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    agent_id: str,
    workflow_type: str | None,
    domain: str | None,
    business_unit: str | None,
    work_item_id: Any,
    prompt: Any,
    model: Any,
    provider: Any,
    tools: Any,
    response_parser: str | Callable[[Any], dict[str, Any] | None] | None,
):
    bound = signature.bind_partial(*args, **kwargs)
    bound.apply_defaults()

    with agent_span(
        agent_id=agent_id,
        domain=domain,
        work_item_id=_resolve_value(work_item_id, bound),
        workflow_type=workflow_type,
        business_unit=business_unit,
    ) as span:
        prompt_value = _resolve_value(prompt, bound)
        if prompt_value is not None:
            span.set_prompt(str(prompt_value))

        try:
            result = await func(*args, **kwargs)
        except Exception as exc:
            span.set_error(exc)
            raise

        _apply_post_call_metadata(
            span,
            bound,
            result,
            model=model,
            provider=provider,
            tools=tools,
            response_parser=response_parser,
        )
        return result


def _invoke_instrumented_sync(
    func: Callable[..., Any],
    signature: inspect.Signature,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    agent_id: str,
    workflow_type: str | None,
    domain: str | None,
    business_unit: str | None,
    work_item_id: Any,
    prompt: Any,
    model: Any,
    provider: Any,
    tools: Any,
    response_parser: str | Callable[[Any], dict[str, Any] | None] | None,
):
    bound = signature.bind_partial(*args, **kwargs)
    bound.apply_defaults()

    with agent_span(
        agent_id=agent_id,
        domain=domain,
        work_item_id=_resolve_value(work_item_id, bound),
        workflow_type=workflow_type,
        business_unit=business_unit,
    ) as span:
        prompt_value = _resolve_value(prompt, bound)
        if prompt_value is not None:
            span.set_prompt(str(prompt_value))

        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            span.set_error(exc)
            raise

        _apply_post_call_metadata(
            span,
            bound,
            result,
            model=model,
            provider=provider,
            tools=tools,
            response_parser=response_parser,
        )
        return result


def _apply_post_call_metadata(
    span,
    bound: inspect.BoundArguments,
    result: Any,
    *,
    model: Any,
    provider: Any,
    tools: Any,
    response_parser: str | Callable[[Any], dict[str, Any] | None] | None,
) -> None:
    parsed = _parse_response(result, response_parser)

    model_value = _resolve_value(model, bound, result=result, span=span)
    if model_value is None:
        model_value = parsed.get("model")

    provider_value = _resolve_value(provider, bound, result=result, span=span)
    if provider_value is None:
        provider_value = parsed.get("provider")

    if model_value is not None:
        span.set_model(str(model_value), provider=str(provider_value) if provider_value else None)

    completion = parsed.get("completion")
    if completion is not None:
        span.set_completion(str(completion))

    input_tokens = _as_int(parsed.get("input_tokens"))
    output_tokens = _as_int(parsed.get("output_tokens"))
    if input_tokens or output_tokens:
        span.set_tokens(input=input_tokens, output=output_tokens)

    for spec in _normalize_tools(_resolve_value(tools, bound, result=result, span=span)):
        span.add_tool_call(
            spec.tool_name,
            status=spec.status,
            duration_ms=spec.duration_ms,
            error=spec.error,
        )


def _resolve_value(
    value: Any,
    bound: inspect.BoundArguments,
    *,
    result: Any = _MISSING,
    span: Any = None,
) -> Any:
    if value is None:
        return None

    if callable(value):
        return _call_resolver(value, bound, result=result, span=span)

    if isinstance(value, str):
        if "{" in value and "}" in value:
            return _render_template(value, bound, result=result, span=span)

        resolved = _lookup_path(value, bound.arguments, result=result, span=span)
        if resolved is not _MISSING:
            return resolved

    return value


def _call_resolver(
    resolver: Callable[..., Any],
    bound: inspect.BoundArguments,
    *,
    result: Any = _MISSING,
    span: Any = None,
) -> Any:
    namespace = dict(bound.arguments)
    if result is not _MISSING:
        namespace["result"] = result
        namespace["response"] = result
    if span is not None:
        namespace["span"] = span

    try:
        signature = inspect.signature(resolver)
    except (TypeError, ValueError):
        return resolver()

    kwargs: dict[str, Any] = {}
    args: list[Any] = []
    has_var_args = False
    has_var_kwargs = False

    for param in signature.parameters.values():
        if param.kind is inspect.Parameter.VAR_POSITIONAL:
            has_var_args = True
            continue
        if param.kind is inspect.Parameter.VAR_KEYWORD:
            has_var_kwargs = True
            continue
        if param.name in namespace:
            kwargs[param.name] = namespace[param.name]

    if has_var_args:
        args.extend(bound.args)
        if result is not _MISSING:
            args.append(result)
    if has_var_kwargs:
        for key, item in namespace.items():
            kwargs.setdefault(key, item)

    return resolver(*args, **kwargs)


def _render_template(
    template: str,
    bound: inspect.BoundArguments,
    *,
    result: Any = _MISSING,
    span: Any = None,
) -> str:
    def replace(match: re.Match[str]) -> str:
        path = match.group(1).strip()
        value = _lookup_path(path, bound.arguments, result=result, span=span)
        if value is _MISSING or value is None:
            return ""
        return str(value)

    return _TEMPLATE_PATTERN.sub(replace, template)


def _lookup_path(path: str, source: dict[str, Any], *, result: Any = _MISSING, span: Any = None) -> Any:
    namespace = dict(source)
    if result is not _MISSING:
        namespace["result"] = result
        namespace["response"] = result
    if span is not None:
        namespace["span"] = span

    parts = [part for part in path.split(".") if part]
    if not parts:
        return _MISSING
    if parts[0] not in namespace:
        return _MISSING

    current = namespace[parts[0]]
    for part in parts[1:]:
        if current is None:
            return _MISSING
        if isinstance(current, dict):
            if part not in current:
                return _MISSING
            current = current[part]
            continue
        if isinstance(current, (list, tuple)) and part.isdigit():
            index = int(part)
            if index >= len(current):
                return _MISSING
            current = current[index]
            continue
        if hasattr(current, part):
            current = getattr(current, part)
            continue
        return _MISSING
    return current


def _parse_response(
    result: Any,
    parser: str | Callable[[Any], dict[str, Any] | None] | None,
) -> dict[str, Any]:
    if result is None or parser is None:
        return {}

    if callable(parser):
        parsed = parser(result)
        return _normalize_parsed_response(parsed)

    parser_name = parser
    if parser_name == "auto":
        parser_name = _infer_parser(result)

    if parser_name == "openai":
        return _normalize_parsed_response(_parse_openai_response(result))
    if parser_name == "anthropic":
        return _normalize_parsed_response(_parse_anthropic_response(result))
    return {}


def _infer_parser(result: Any) -> str | None:
    if _read(result, "choices") is not None:
        return "openai"
    if _read(result, "content") is not None and _read(result, "usage") is not None:
        return "anthropic"
    return None


def _parse_openai_response(result: Any) -> dict[str, Any]:
    usage = _read(result, "usage")
    completion = _read(result, "output_text")
    if completion is None:
        choices = _read(result, "choices") or []
        if choices:
            message = _read(choices[0], "message")
            completion = _coerce_text(_read(message, "content"))

    # Extract cache and reasoning tokens from provider response
    prompt_tokens_details = _read(usage, "prompt_tokens_details") or {}
    completion_tokens_details = _read(usage, "completion_tokens_details") or {}

    return {
        "provider": "openai",
        "model": _read(result, "model"),
        "completion": completion,
        "input_tokens": _read(usage, "prompt_tokens"),
        "output_tokens": _read(usage, "completion_tokens"),
        "cache_read_tokens": _read(prompt_tokens_details, "cached_tokens"),
        "reasoning_tokens": _read(completion_tokens_details, "reasoning_tokens"),
    }


def _parse_anthropic_response(result: Any) -> dict[str, Any]:
    usage = _read(result, "usage")
    return {
        "provider": "anthropic",
        "model": _read(result, "model"),
        "completion": _coerce_text(_read(result, "content")),
        "input_tokens": _read(usage, "input_tokens"),
        "output_tokens": _read(usage, "output_tokens"),
        "cache_creation_tokens": _read(usage, "cache_creation_input_tokens"),
        "cache_read_tokens": _read(usage, "cache_read_input_tokens"),
    }


def _normalize_parsed_response(parsed: dict[str, Any] | None) -> dict[str, Any]:
    if not parsed:
        return {}
    return {
        "provider": parsed.get("provider"),
        "model": parsed.get("model"),
        "completion": parsed.get("completion"),
        "input_tokens": parsed.get("input_tokens", parsed.get("input")),
        "output_tokens": parsed.get("output_tokens", parsed.get("output")),
        "cache_read_tokens": parsed.get("cache_read_tokens"),
        "cache_creation_tokens": parsed.get("cache_creation_tokens"),
        "reasoning_tokens": parsed.get("reasoning_tokens"),
    }


def _normalize_tools(value: Any) -> list[ToolCallSpec]:
    if value is None:
        return []
    if isinstance(value, ToolCallSpec):
        return [value]
    if isinstance(value, str):
        return [ToolCallSpec(tool_name=value)]
    if isinstance(value, dict):
        return [
            ToolCallSpec(
                tool_name=str(value["tool_name"]),
                status=str(value.get("status", "success")),
                duration_ms=_as_int(value.get("duration_ms")) if value.get("duration_ms") is not None else None,
                error=str(value["error"]) if value.get("error") is not None else None,
            )
        ]

    normalized: list[ToolCallSpec] = []
    for item in value:
        normalized.extend(_normalize_tools(item))
    return normalized


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = [_coerce_text(part) for part in value]
        text = "\n".join(part for part in parts if part)
        return text or None
    if isinstance(value, dict):
        if value.get("text") is not None:
            return str(value["text"])
        if value.get("content") is not None:
            return _coerce_text(value["content"])
    if hasattr(value, "text") and getattr(value, "text") is not None:
        return str(getattr(value, "text"))
    if hasattr(value, "content") and getattr(value, "content") is not None:
        return _coerce_text(getattr(value, "content"))
    return str(value)


def _as_int(value: Any) -> int:
    if value is None:
        return 0
    return int(value)


def _read(obj: Any, key: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)
