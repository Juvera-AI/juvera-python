"""Juvera SDK — open instrumentation for AI agents."""
from __future__ import annotations

__version__ = "0.2.2"
from juvera_sdk.config import JuveraConfig
import juvera_sdk.tracer as _tracer

_config: JuveraConfig | None = None


def init(
    api_key: str | None = None,
    org_id: str | None = None,
    endpoint: str | None = None,
    service_name: str | None = None,
    domain: str | None = None,
    agent_id: str | None = None,
    environment: str | None = None,
    debug: bool | None = None,
    workflow_baselines: dict | None = None,
    _exporter=None,   # test hook
) -> None:
    """Configure the SDK. Call once at startup before any spans.

    All parameters are optional — reads from env vars if not provided:
        JUVERA_API_KEY, JUVERA_ORG_ID, JUVERA_ENDPOINT, JUVERA_SERVICE_NAME,
        JUVERA_DOMAIN, JUVERA_AGENT_ID, JUVERA_ENVIRONMENT, JUVERA_DEBUG
    """
    global _config
    overrides = {
        k: v for k, v in {
            "api_key": api_key, "org_id": org_id, "endpoint": endpoint,
            "service_name": service_name, "domain": domain, "agent_id": agent_id,
            "environment": environment,
            "debug": debug, "workflow_baselines": workflow_baselines,
        }.items() if v is not None
    }
    _config = JuveraConfig.from_env(**overrides)
    _tracer.setup_provider(_config, _exporter=_exporter)


def _get_config() -> JuveraConfig:
    if _config is None:
        raise RuntimeError("juvera.init() must be called before using the SDK")
    return _config


def flush() -> None:
    _tracer.flush()


def shutdown() -> None:
    global _config
    _tracer.shutdown()
    _config = None


from juvera_sdk.span import agent_span          # noqa: E402
from juvera_sdk.signals import record_impact_signal  # noqa: E402
from juvera_sdk.handoff import record_handoff   # noqa: E402
from juvera_sdk.context import (  # noqa: E402
    clear_context,
    clear_work_item,
    context,
    set_context,
    set_work_item,
    workflow,
)
from juvera_sdk.events import record_event       # noqa: E402
from juvera_sdk.roi import estimate_roi          # noqa: E402
from juvera_sdk.frameworks import (  # noqa: E402
    instrument_autogen,
    instrument_crewai,
    instrument_langchain,
    instrument_langgraph,
    instrument_openai_agents,
)
from juvera_sdk.wrappers import wrap_anthropic, wrap_openai, wrap_openai_responses  # noqa: E402
from juvera_sdk.decorators import (  # noqa: E402
    anthropic_agent,
    instrument,
    openai_agent,
    response_text,
    tool_call,
)


# ── Shortcuts ────────────────────────────────────────────────────────────────

def agent(agent_id: str, **kwargs):
    """Simplified decorator — auto-detects provider from response.

    Usage:
        @j.agent("my_agent")
        def my_function(...):
            return client.messages.create(...)  # or client.chat.completions.create(...)
    """
    return instrument(agent_id, response_parser="auto", **kwargs)


def impact(
    impact_type: str,
    value: float,
    *,
    impact_category: str = "general",
    domain: str | None = None,
    source: str | None = None,
    **properties,
) -> None:
    """Shorthand for record_impact_signal.

    Usage:
        j.impact("cost_reduction", 22.0, source="zendesk")
    """
    record_impact_signal(
        impact_type=impact_type,
        value=value,
        impact_category=impact_category,
        domain=domain,
        source_system=source,
        properties=properties if properties else None,
    )


def get_plugin_path() -> str:
    """Return path to the Claude Code plugin directory."""
    import os
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "claude-plugin")


__all__ = [
    "__version__", "init", "agent_span", "record_impact_signal",
    "record_handoff", "record_event", "estimate_roi",
    "set_work_item", "clear_work_item", "workflow",
    "context", "set_context", "clear_context",
    "instrument", "openai_agent", "anthropic_agent", "tool_call", "response_text",
    "wrap_openai", "wrap_openai_responses", "wrap_anthropic",
    "instrument_openai_agents", "instrument_langgraph", "instrument_langchain",
    "instrument_crewai", "instrument_autogen",
    "agent", "impact",
    "flush", "shutdown", "get_plugin_path",
]
