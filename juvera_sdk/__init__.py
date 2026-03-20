"""Juvera SDK — open instrumentation for AI agents."""
from __future__ import annotations

__version__ = "0.1.3"
from juvera_sdk.config import JuveraConfig
import juvera_sdk.tracer as _tracer

_config: JuveraConfig | None = None


def init(
    api_key: str,
    org_id: str,
    endpoint: str = "https://ingest.juvera.ai",
    service_name: str = "juvera-agent",
    domain: str | None = None,
    agent_id: str | None = None,
    debug: bool = False,
    _exporter=None,   # test hook
) -> None:
    """Configure the SDK. Call once at startup before any spans."""
    global _config
    _config = JuveraConfig(
        api_key=api_key, org_id=org_id, endpoint=endpoint,
        service_name=service_name, domain=domain, agent_id=agent_id, debug=debug,
    )
    _tracer.setup_provider(_config, exporter=_exporter)


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

__all__ = [
    "__version__", "init", "agent_span", "record_impact_signal",
    "record_handoff", "flush", "shutdown",
]
