"""TracerProvider setup and management."""
from __future__ import annotations
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from juvera_sdk.config import JuveraConfig
from juvera_sdk.processor import JuveraSpanProcessor

_provider: TracerProvider | None = None


def _get_version() -> str:
    from juvera_sdk import __version__
    return __version__


def setup_provider(config: JuveraConfig, _exporter=None) -> TracerProvider:
    """Create and register a TracerProvider with JuveraSpanProcessor."""
    global _provider

    resource = Resource.create({
        "service.name": config.service_name,
        "juvera.org_id": config.org_id,
        "juvera.domain": config.domain or "",
        "juvera.agent_id": config.agent_id or "",
        "juvera.environment": config.environment or ("dev" if config.debug else "prod"),
        "juvera.sdk_version": _get_version(),
    })

    _provider = TracerProvider(resource=resource)
    _provider.add_span_processor(
        JuveraSpanProcessor(
            api_key=config.api_key,
            org_id=config.org_id,
            endpoint=config.endpoint,
            debug=config.debug,
            domain=config.domain,
            _exporter=_exporter,
        )
    )

    trace.set_tracer_provider(_provider)
    return _provider


def get_tracer(name: str = "juvera-sdk") -> trace.Tracer:
    if _provider is not None:
        return _provider.get_tracer(name)
    return trace.get_tracer(name)


def flush() -> None:
    if _provider:
        _provider.force_flush()


def shutdown() -> None:
    global _provider
    if _provider:
        _provider.shutdown()
        _provider = None
