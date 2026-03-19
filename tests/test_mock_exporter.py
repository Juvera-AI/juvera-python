from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from juvera_sdk.exporters.mock import MockExporter


def test_mock_exporter_captures_spans():
    exporter = MockExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test")

    with tracer.start_as_current_span("test.span") as span:
        span.set_attribute("juvera.agent_id", "agent_01")

    assert exporter.span_count() == 1
    assert exporter.last_span().attributes.get("juvera.agent_id") == "agent_01"


def test_mock_exporter_clear():
    exporter = MockExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test")

    with tracer.start_as_current_span("s1"):
        pass
    assert exporter.span_count() == 1

    exporter.clear()
    assert exporter.span_count() == 0
