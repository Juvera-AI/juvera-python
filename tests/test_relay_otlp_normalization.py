"""relay captures (OTLP envelopes) must normalize into demo-shape on disk."""
import json
import os
from juvera_sdk.local_relay import _normalize_otlp_envelope_to_events


def test_otlp_envelope_normalized_to_demo_shape():
    envelope = {
        "resourceSpans": [{
            "scopeSpans": [{
                "spans": [{
                    "spanId": "abc123",
                    "startTimeUnixNano": "1700000000000000000",
                    "endTimeUnixNano":   "1700000003200000000",
                    "status": {"code": 1},  # STATUS_CODE_OK
                    "attributes": [
                        {"key": "juvera.agent.id", "value": {"stringValue": "support_agent"}},
                        {"key": "juvera.workflow.type", "value": {"stringValue": "ticket_deflection"}},
                        {"key": "juvera.work_item_id", "value": {"stringValue": "wi_42"}},
                        {"key": "gen_ai.request.model", "value": {"stringValue": "gpt-4o-mini"}},
                        {"key": "gen_ai.system", "value": {"stringValue": "openai"}},
                        {"key": "gen_ai.usage.input_tokens", "value": {"intValue": "421"}},
                        {"key": "gen_ai.usage.output_tokens", "value": {"intValue": "187"}},
                    ],
                }],
            }],
        }],
    }
    events = list(_normalize_otlp_envelope_to_events(envelope))
    assert len(events) == 1
    e = events[0]
    assert e["source"] == "capture"
    assert e["agent_id"] == "support_agent"
    assert e["workflow_type"] == "ticket_deflection"
    assert e["work_item_id"] == "wi_42"
    assert e["model"] == "gpt-4o-mini"
    assert e["provider"] == "openai"
    assert e["input_tokens"] == 421
    assert e["output_tokens"] == 187
    assert e["duration_ms"] == 3200
    assert e["status"] == "success"
    # Cost catalog-derived
    assert 0.00015 < e["agent_cost_usd"] < 0.00020
    # Savings derived from baseline
    assert e["estimated_savings_usd"] is not None
    assert e["estimated_savings_usd"] > 21.0


def test_non_otlp_envelope_falls_through_unchanged():
    """Anything without resourceSpans should be passed through as a single event (back-compat)."""
    envelope = {"some_other_field": "value"}
    events = list(_normalize_otlp_envelope_to_events(envelope))
    assert len(events) == 1
    assert events[0]["some_other_field"] == "value"
    assert events[0]["source"] == "capture"


def test_normalizer_accepts_prompt_completion_token_aliases():
    """Phoenix/OpenInference style prompt_tokens/completion_tokens must be honored."""
    envelope = {
        "resourceSpans": [{"scopeSpans": [{"spans": [{
            "spanId": "phoenix1",
            "startTimeUnixNano": "0", "endTimeUnixNano": "1000000",
            "status": {"code": 1},
            "attributes": [
                {"key": "juvera.workflow_type", "value": {"stringValue": "ticket_deflection"}},
                {"key": "gen_ai.request.model", "value": {"stringValue": "gpt-4o-mini"}},
                {"key": "gen_ai.system", "value": {"stringValue": "openai"}},
                # Phoenix uses prompt_tokens / completion_tokens
                {"key": "gen_ai.usage.prompt_tokens", "value": {"intValue": "421"}},
                {"key": "gen_ai.usage.completion_tokens", "value": {"intValue": "187"}},
            ],
        }]}]}],
    }
    events = list(_normalize_otlp_envelope_to_events(envelope))
    assert len(events) == 1
    e = events[0]
    assert e["input_tokens"] == 421
    assert e["output_tokens"] == 187
    # Cost should be non-zero (catalog-derived from the alias-recognized tokens)
    assert e["agent_cost_usd"] > 0
    assert 0.00015 < e["agent_cost_usd"] < 0.00020


def test_normalizer_accepts_juvera_agent_id_canonical():
    """Canonical SDK attribute juvera.agent_id (no .id suffix) must be recognized."""
    envelope = {
        "resourceSpans": [{"scopeSpans": [{"spans": [{
            "spanId": "sdk1",
            "startTimeUnixNano": "0", "endTimeUnixNano": "1000000",
            "status": {"code": 1},
            "attributes": [
                {"key": "juvera.agent_id", "value": {"stringValue": "support_agent"}},
                {"key": "juvera.workflow_type", "value": {"stringValue": "ticket_deflection"}},
            ],
        }]}]}],
    }
    events = list(_normalize_otlp_envelope_to_events(envelope))
    assert len(events) == 1
    assert events[0]["agent_id"] == "support_agent"
    assert events[0]["workflow_type"] == "ticket_deflection"


def test_otlp_error_status_marks_event_error():
    envelope = {
        "resourceSpans": [{"scopeSpans": [{"spans": [{
            "spanId": "err1",
            "startTimeUnixNano": "0", "endTimeUnixNano": "1000000",
            "status": {"code": 2},  # STATUS_CODE_ERROR
            "attributes": [
                {"key": "exception.message", "value": {"stringValue": "boom"}},
            ],
        }]}]}],
    }
    events = list(_normalize_otlp_envelope_to_events(envelope))
    assert events[0]["status"] == "error"
    assert events[0]["error"] == "boom"
