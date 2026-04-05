"""Framework-aware instrumentation entrypoints with lazy imports."""
from __future__ import annotations

import importlib
import inspect
from functools import wraps
from typing import Any, Callable

from juvera_sdk.span import agent_span

_ctx = importlib.import_module("juvera_sdk.context")


def _missing_extra(extra: str, packages: list[str]) -> ImportError:
    package_list = ", ".join(packages)
    return ImportError(
        f"Install the `{extra}` extra to use this helper. Expected one of: {package_list}. "
        f"Example: pip install 'juvera-sdk[{extra}]'"
    )


def _import_first(paths: list[tuple[str, str]], *, extra: str, packages: list[str]) -> Any:
    for module_name, attr_name in paths:
        try:
            module = importlib.import_module(module_name)
            return getattr(module, attr_name)
        except (ImportError, AttributeError):
            continue
    raise _missing_extra(extra, packages)


def _resolve_framework_agent_id(explicit_agent_id: str | None, candidate: Any, fallback: str) -> str:
    if explicit_agent_id:
        return explicit_agent_id
    active_agent_id = _ctx.get_agent_id()
    if active_agent_id:
        return active_agent_id
    for attr in ("name", "agent_id", "id"):
        value = getattr(candidate, attr, None)
        if value:
            return str(value)
    return fallback


def _wrap_with_agent_span(
    func: Callable[..., Any],
    *,
    agent_id: str | None,
    default_workflow_type: str | None,
    domain: str | None,
    business_unit: str | None,
    fallback_agent_id: str,
) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        if _ctx.get_current_span() is not None:
            return func(*args, **kwargs)

        resolved_agent_id = _resolve_framework_agent_id(agent_id, args[0] if args else None, fallback_agent_id)
        context_manager = agent_span(
            agent_id=resolved_agent_id,
            workflow_type=default_workflow_type,
            domain=domain,
            business_unit=business_unit,
        )
        span = context_manager.__enter__()
        span.set_attribute("juvera.framework", fallback_agent_id)
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            span.set_error(exc)
            context_manager.__exit__(type(exc), exc, exc.__traceback__)
            raise

        if inspect.isawaitable(result):
            async def _await_result():
                try:
                    return await result
                except Exception as exc:
                    span.set_error(exc)
                    raise
                finally:
                    context_manager.__exit__(None, None, None)

            return _await_result()

        context_manager.__exit__(None, None, None)
        return result

    return wrapper


def _patch_method(obj: Any, name: str, wrapper_builder: Callable[[Callable[..., Any]], Callable[..., Any]]) -> bool:
    original = getattr(obj, name, None)
    if original is None or getattr(original, "__juvera_wrapped__", False):
        return False
    wrapped = wrapper_builder(original)
    setattr(wrapped, "__juvera_wrapped__", True)
    setattr(obj, name, wrapped)
    return True


def instrument_openai_agents(
    *,
    agent_id: str | None = None,
    default_workflow_type: str | None = None,
    domain: str | None = None,
    business_unit: str | None = None,
) -> dict[str, Any]:
    """Patch the OpenAI Agents runner so top-level runs emit a Juvera span."""

    try:
        runner_module = importlib.import_module("agents")
    except ImportError as exc:
        raise _missing_extra("openai-agents", ["openai-agents", "agents"]) from exc

    runner = getattr(runner_module, "Runner", None)
    if runner is None:
        raise _missing_extra("openai-agents", ["openai-agents", "agents"])

    patched = 0
    for method_name in ("run", "run_sync", "stream"):
        patched += int(
            _patch_method(
                runner,
                method_name,
                lambda func: _wrap_with_agent_span(
                    func,
                    agent_id=agent_id,
                    default_workflow_type=default_workflow_type,
                    domain=domain,
                    business_unit=business_unit,
                    fallback_agent_id="openai_agents",
                ),
            )
        )
    return {"framework": "openai_agents", "patchedMethods": patched}


def instrument_langchain(**kwargs: Any) -> Any:
    """Delegate to an installed LangChain instrumentor."""

    instrumentor_cls = _import_first(
        [
            ("openinference.instrumentation.langchain", "LangChainInstrumentor"),
            ("opentelemetry.instrumentation.langchain", "LangchainInstrumentor"),
        ],
        extra="langchain",
        packages=["openinference-instrumentation-langchain", "opentelemetry-instrumentation-langchain"],
    )
    instrumentor = instrumentor_cls()
    instrumentor.instrument(**kwargs)
    return instrumentor


def instrument_langgraph(**kwargs: Any) -> Any:
    """Delegate to an installed LangGraph instrumentor."""

    instrumentor_cls = _import_first(
        [
            ("openinference.instrumentation.langgraph", "LangGraphInstrumentor"),
            ("opentelemetry.instrumentation.langchain", "LangchainInstrumentor"),
        ],
        extra="langgraph",
        packages=["openinference-instrumentation-langgraph", "opentelemetry-instrumentation-langchain"],
    )
    instrumentor = instrumentor_cls()
    instrumentor.instrument(**kwargs)
    return instrumentor


def instrument_crewai(
    *,
    agent_id: str | None = None,
    default_workflow_type: str | None = None,
    domain: str | None = None,
    business_unit: str | None = None,
) -> dict[str, Any]:
    """Patch CrewAI kickoff methods so a Juvera workflow span surrounds crew execution."""

    try:
        crewai = importlib.import_module("crewai")
    except ImportError as exc:
        raise _missing_extra("crewai", ["crewai"]) from exc

    crew_cls = getattr(crewai, "Crew", None)
    if crew_cls is None:
        raise _missing_extra("crewai", ["crewai"])

    patched = 0
    for method_name in ("kickoff", "kickoff_async"):
        patched += int(
            _patch_method(
                crew_cls,
                method_name,
                lambda func: _wrap_with_agent_span(
                    func,
                    agent_id=agent_id,
                    default_workflow_type=default_workflow_type,
                    domain=domain,
                    business_unit=business_unit,
                    fallback_agent_id="crewai",
                ),
            )
        )
    return {"framework": "crewai", "patchedMethods": patched}


def instrument_autogen(
    *,
    agent_id: str | None = None,
    default_workflow_type: str | None = None,
    domain: str | None = None,
    business_unit: str | None = None,
) -> dict[str, Any]:
    """Patch common AutoGen agent entrypoints so chats emit a Juvera workflow span."""

    try:
        autogen = importlib.import_module("autogen")
    except ImportError as exc:
        raise _missing_extra("autogen", ["pyautogen", "autogen"]) from exc

    patched = 0
    for class_name, method_names in {
        "AssistantAgent": ("run", "a_run", "initiate_chat"),
        "ConversableAgent": ("initiate_chat", "a_initiate_chat"),
    }.items():
        cls = getattr(autogen, class_name, None)
        if cls is None:
            continue
        for method_name in method_names:
            patched += int(
                _patch_method(
                    cls,
                    method_name,
                    lambda func: _wrap_with_agent_span(
                        func,
                        agent_id=agent_id,
                        default_workflow_type=default_workflow_type,
                        domain=domain,
                        business_unit=business_unit,
                        fallback_agent_id="autogen",
                    ),
                )
            )
    if patched == 0:
        raise _missing_extra("autogen", ["pyautogen", "autogen"])
    return {"framework": "autogen", "patchedMethods": patched}
