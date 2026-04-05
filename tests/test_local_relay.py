from juvera_sdk.local_relay import build_proxy_trace_envelope, enrich_trace_envelope, inspect_trace_envelope


def test_inspect_trace_envelope_detects_attribution_ready_sdk_batch():
    envelope = {
        "resourceSpans": [
            {
                "resource": {"attributes": []},
                "scopeSpans": [
                    {
                        "scope": {"name": "juvera-sdk"},
                        "spans": [
                            {
                                "traceId": "a" * 32,
                                "spanId": "b" * 16,
                                "name": "agent.run",
                                "startTimeUnixNano": "1",
                                "endTimeUnixNano": "2",
                                "attributes": [
                                    {"key": "juvera.agent_id", "value": {"stringValue": "agent_01"}},
                                    {"key": "juvera.workflow_type", "value": {"stringValue": "support_ticket_resolution"}},
                                    {"key": "juvera.work_item_id", "value": {"stringValue": "wi_123"}},
                                ],
                            }
                        ],
                    }
                ],
            }
        ]
    }

    metadata = inspect_trace_envelope(envelope)
    assert metadata["sourceMode"] == "sdk"
    assert metadata["instrumentationReadiness"] == "attribution_ready"
    assert metadata["requiredFields"]["work_item_id"] is True


def test_enrich_trace_envelope_adds_capture_metadata():
    envelope = {
        "resourceSpans": [{"resource": {"attributes": []}, "scopeSpans": [{"scope": {"name": "otel"}, "spans": [{"attributes": []}]}]}]
    }
    enriched, metadata = enrich_trace_envelope(envelope, "session-123")
    attrs = enriched["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["attributes"]
    keys = {item["key"] for item in attrs}
    assert "juvera.capture_source" in keys
    assert "juvera.instrumentation_readiness" in keys
    assert metadata["sourceMode"] == "attach"


def test_build_proxy_trace_envelope_is_always_provisional():
    envelope, metadata = build_proxy_trace_envelope(
        provider="openai",
        request_json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hello"}]},
        response_json={
            "model": "gpt-4o-mini",
            "choices": [{"message": {"content": "Hi there"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 8},
        },
        duration_ms=42.0,
        session_id="relay-session",
    )
    attrs = envelope["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["attributes"]
    values = {item["key"]: item["value"] for item in attrs}
    assert values["juvera.capture_source"]["stringValue"] == "proxy"
    assert values["juvera.instrumentation_readiness"]["stringValue"] == "provisional"
    assert metadata["requiredFields"]["work_item_id"] is False
