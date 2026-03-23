import pytest
from unittest.mock import MagicMock
from opentelemetry.sdk.trace import ReadableSpan
from juvera_sdk.compliance.pii import scan_span_for_pii, PiiMatch


def _make_span(attrs: dict) -> MagicMock:
    span = MagicMock(spec=ReadableSpan)
    span.attributes = attrs
    span.name = "agent.run"
    span.context = MagicMock()
    span.context.trace_id = 0x1234567890ABCDEF
    return span


def test_detects_email():
    span = _make_span({"gen_ai.output": "Contact us at john@example.com for help"})
    matches = scan_span_for_pii(span)
    assert len(matches) >= 1
    assert any(m.pii_type == "email" and m.confidence == "high" for m in matches)


def test_detects_ssn():
    span = _make_span({"user.input": "My SSN is 123-45-6789"})
    matches = scan_span_for_pii(span)
    assert any(m.pii_type == "ssn" and m.confidence == "high" for m in matches)


def test_detects_credit_card():
    span = _make_span({"gen_ai.output": "Card: 4111-1111-1111-1111"})
    matches = scan_span_for_pii(span)
    assert any(m.pii_type == "credit_card" for m in matches)


def test_detects_phone():
    span = _make_span({"gen_ai.output": "Call me at 555-123-4567"})
    matches = scan_span_for_pii(span)
    assert any(m.pii_type == "phone" for m in matches)


def test_detects_api_key():
    span = _make_span({"gen_ai.output": "Use key sk-abcdefghijklmnopqrstuvwxyz"})
    matches = scan_span_for_pii(span)
    assert any(m.pii_type == "api_key" for m in matches)


def test_no_false_positive_on_clean_text():
    span = _make_span({"gen_ai.output": "The order was processed successfully."})
    matches = scan_span_for_pii(span)
    assert len(matches) == 0


def test_skips_non_string_attributes():
    span = _make_span({
        "gen_ai.usage.input_tokens": 420,
        "juvera.human_required": True,
        "gen_ai.usage.cost": 0.05,
    })
    matches = scan_span_for_pii(span)
    assert len(matches) == 0


def test_skips_sequence_attributes():
    span = _make_span({"tool.names": ["lookup_crm", "search_kb"]})
    matches = scan_span_for_pii(span)
    assert len(matches) == 0


def test_multiple_pii_in_same_attribute():
    span = _make_span({
        "gen_ai.output": "Email john@example.com, SSN 123-45-6789"
    })
    matches = scan_span_for_pii(span)
    types = {m.pii_type for m in matches}
    assert "email" in types
    assert "ssn" in types


def test_match_includes_span_attribute_name():
    span = _make_span({"my.custom.attr": "email is test@test.com"})
    matches = scan_span_for_pii(span)
    assert matches[0].span_attribute == "my.custom.attr"
