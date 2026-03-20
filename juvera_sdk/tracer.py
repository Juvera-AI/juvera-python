"""TracerProvider setup and management."""
from __future__ import annotations
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.sdk.resources import Resource
from juvera_sdk.config import JuveraConfig
from juvera_sdk.exporters.debug import DebugExporter
from juvera_sdk.exporters.http import JuveraSpanExporter

_provider: TracerProvider | None = None


def setup_provider(config: JuveraConfig, exporter=None) -> TracerProvider:
    """Create and register a TracerProvider. exporter kwarg overrides for tests."""
    global _provider

    resource = Resource.create({
        "service.name": config.service_name,
        "juvera.org_id": config.org_id,
        "juvera.domain": config.domain or "",
        "juvera.agent_id": config.agent_id or "",
        "juvera.environment": "production" if not config.debug else "dev",
        "juvera.sdk_version": "0.1.3",
    })

    _provider = TracerProvider(resource=resource)

    if exporter is None:
        if config.is_local:
            exporter = DebugExporter()
        else:
            exporter = JuveraSpanExporter(config)

    # Debug/test mode: SimpleSpanProcessor (synchronous, no buffering)
    # Production mode: BatchSpanProcessor
    if config.is_local or config.debug:
        _provider.add_span_processor(SimpleSpanProcessor(exporter))
    else:
        _provider.add_span_processor(BatchSpanProcessor(exporter))

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
