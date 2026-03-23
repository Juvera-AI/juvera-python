import pytest
from opentelemetry.sdk.trace import TracerProvider
from juvera_sdk.processor import JuveraSpanProcessor
from juvera_sdk.exporters.mock import MockExporter


def test_processor_routes_to_exporter(mock_exporter):
    provider = TracerProvider()
    processor = JuveraSpanProcessor(
        api_key="jvr_test", org_id="org_test",
        endpoint="local", _exporter=mock_exporter,
    )
    provider.add_span_processor(processor)
    tracer = provider.get_tracer("test")
    with tracer.start_as_current_span("agent.run") as span:
        span.set_attribute("juvera.agent_id", "agent_01")
    assert mock_exporter.span_count() == 1
    assert mock_exporter.last_span().attributes["juvera.agent_id"] == "agent_01"
    provider.shutdown()


def test_processor_validates_api_key():
    with pytest.raises(ValueError, match="api_key"):
        JuveraSpanProcessor(api_key="", org_id="org_test")


def test_processor_validates_org_id():
    with pytest.raises(ValueError, match="org_id"):
        JuveraSpanProcessor(api_key="jvr_test", org_id="")


def test_processor_pii_warns_in_debug_mode(mock_exporter, capsys):
    provider = TracerProvider()
    processor = JuveraSpanProcessor(
        api_key="jvr_test", org_id="org_test",
        endpoint="local", _exporter=mock_exporter,
    )
    provider.add_span_processor(processor)
    tracer = provider.get_tracer("test")
    with tracer.start_as_current_span("agent.run") as span:
        span.set_attribute("gen_ai.output", "Contact john@example.com")
    captured = capsys.readouterr()
    assert "PII detected" in captured.err
    assert "email" in captured.err
    provider.shutdown()


def test_processor_no_pii_warn_when_disabled(mock_exporter, capsys):
    provider = TracerProvider()
    processor = JuveraSpanProcessor(
        api_key="jvr_test", org_id="org_test",
        endpoint="local", pii_check=False, _exporter=mock_exporter,
    )
    provider.add_span_processor(processor)
    tracer = provider.get_tracer("test")
    with tracer.start_as_current_span("agent.run") as span:
        span.set_attribute("gen_ai.output", "Contact john@example.com")
    captured = capsys.readouterr()
    assert "PII detected" not in captured.err
    provider.shutdown()


def test_processor_no_pii_warn_in_production_mode(mock_exporter, capsys):
    provider = TracerProvider()
    processor = JuveraSpanProcessor(
        api_key="jvr_test", org_id="org_test",
        endpoint="https://ingest.juvera.ai", _exporter=mock_exporter,
    )
    provider.add_span_processor(processor)
    tracer = provider.get_tracer("test")
    with tracer.start_as_current_span("agent.run") as span:
        span.set_attribute("gen_ai.output", "Contact john@example.com")
    captured = capsys.readouterr()
    assert "PII detected" not in captured.err
    provider.shutdown()


def test_processor_force_flush(mock_exporter):
    provider = TracerProvider()
    processor = JuveraSpanProcessor(
        api_key="jvr_test", org_id="org_test",
        endpoint="local", _exporter=mock_exporter,
    )
    provider.add_span_processor(processor)
    tracer = provider.get_tracer("test")
    with tracer.start_as_current_span("test.span"):
        pass
    processor.force_flush()
    assert mock_exporter.span_count() == 1
    provider.shutdown()
