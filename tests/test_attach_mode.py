"""Test JuveraSpanProcessor in attach mode — no j.init() called."""
import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.resources import Resource
from juvera_sdk.processor import JuveraSpanProcessor
from juvera_sdk.exporters.mock import MockExporter


@pytest.fixture
def attach_setup():
    exporter = MockExporter()
    provider = TracerProvider(
        resource=Resource.create({"service.name": "my-phoenix-app"})
    )
    processor = JuveraSpanProcessor(
        api_key="jvr_test", org_id="org_test",
        endpoint="local", _exporter=exporter,
    )
    provider.add_span_processor(processor)
    yield provider, exporter
    provider.shutdown()


def test_attach_mode_spans_flow_through(attach_setup):
    provider, exporter = attach_setup
    tracer = provider.get_tracer("phoenix-tracer")
    with tracer.start_as_current_span("llm.call") as span:
        span.set_attribute("gen_ai.request.model", "gpt-4o")
        span.set_attribute("gen_ai.usage.input_tokens", 500)
    assert exporter.span_count() == 1
    attrs = exporter.last_span().attributes
    assert attrs["gen_ai.request.model"] == "gpt-4o"


def test_attach_mode_no_juvera_init_required(attach_setup):
    """Verify j.init() was NOT called — attach mode is standalone."""
    import juvera_sdk as j
    # In attach mode, _config should be None since init() was never called
    assert j._config is None


def test_attach_mode_pii_warns(attach_setup, capsys):
    provider, exporter = attach_setup
    tracer = provider.get_tracer("test")
    with tracer.start_as_current_span("agent.run") as span:
        span.set_attribute("gen_ai.output", "User email is test@test.com")
    captured = capsys.readouterr()
    assert "PII detected" in captured.err


def test_attach_mode_with_existing_processors():
    """Verify JuveraSpanProcessor works alongside other processors."""
    exporter_juvera = MockExporter()
    exporter_other = MockExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter_other))
    provider.add_span_processor(JuveraSpanProcessor(
        api_key="jvr_test", org_id="org_test",
        endpoint="local", _exporter=exporter_juvera,
    ))
    tracer = provider.get_tracer("test")
    with tracer.start_as_current_span("test.span"):
        pass
    assert exporter_juvera.span_count() == 1
    assert exporter_other.span_count() == 1
    provider.shutdown()
