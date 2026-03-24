# tests/test_normalizer.py
import pytest
from juvera_sdk.exporters.mock import MockExporter


def test_phoenix_input_normalized(attach_setup):
    provider, exporter = attach_setup
    tracer = provider.get_tracer("phoenix")
    with tracer.start_as_current_span("llm.call") as span:
        span.set_attribute("input.value", "Hello world")
        span.set_attribute("output.value", "Hi there")
    attrs = dict(exporter.last_span().attributes)
    assert attrs["gen_ai.prompt"] == "Hello world"
    assert attrs["gen_ai.completion"] == "Hi there"


def test_langfuse_input_normalized(attach_setup):
    provider, exporter = attach_setup
    tracer = provider.get_tracer("langfuse")
    with tracer.start_as_current_span("generation") as span:
        span.set_attribute("langfuse.input", "Query text")
    attrs = dict(exporter.last_span().attributes)
    assert attrs["gen_ai.prompt"] == "Query text"


def test_explicit_juvera_attr_not_overwritten(attach_setup):
    provider, exporter = attach_setup
    tracer = provider.get_tracer("test")
    with tracer.start_as_current_span("llm.call") as span:
        span.set_attribute("gen_ai.prompt", "explicit prompt")
        span.set_attribute("input.value", "phoenix prompt")
    attrs = dict(exporter.last_span().attributes)
    assert attrs["gen_ai.prompt"] == "explicit prompt"


def test_token_count_normalization(attach_setup):
    provider, exporter = attach_setup
    tracer = provider.get_tracer("phoenix")
    with tracer.start_as_current_span("llm.call") as span:
        span.set_attribute("llm.token_count.prompt", 500)
        span.set_attribute("llm.token_count.completion", 200)
    attrs = dict(exporter.last_span().attributes)
    assert attrs["gen_ai.usage.input_tokens"] == 500
    assert attrs["gen_ai.usage.output_tokens"] == 200


def test_no_normalization_passes_through(attach_setup):
    provider, exporter = attach_setup
    tracer = provider.get_tracer("test")
    with tracer.start_as_current_span("agent.run") as span:
        span.set_attribute("gen_ai.request.model", "gpt-4o")
    attrs = dict(exporter.last_span().attributes)
    assert attrs["gen_ai.request.model"] == "gpt-4o"


def test_braintrust_normalized(attach_setup):
    provider, exporter = attach_setup
    tracer = provider.get_tracer("braintrust")
    with tracer.start_as_current_span("eval") as span:
        span.set_attribute("braintrust.input", "Eval input")
        span.set_attribute("braintrust.output", "Eval output")
    attrs = dict(exporter.last_span().attributes)
    assert attrs["gen_ai.prompt"] == "Eval input"
    assert attrs["gen_ai.completion"] == "Eval output"
