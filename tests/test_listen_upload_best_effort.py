"""Cloud upload errors must not crash the relay; capture continues."""
import respx
import httpx
import pytest


@respx.mock
def test_upload_failure_does_not_propagate():
    from juvera_sdk.local_relay import _try_upload_capture

    respx.post("https://ingest.juvera.ai/v1/traces").mock(
        return_value=httpx.Response(500, text="server error")
    )
    ok = _try_upload_capture(
        endpoint="https://ingest.juvera.ai",
        api_key="jvr_test", org_id="org_test",
        payload={"spans": [{"id": "s1"}]},
    )
    assert ok is False


@respx.mock
def test_upload_network_error_does_not_propagate():
    from juvera_sdk.local_relay import _try_upload_capture

    respx.post("https://ingest.juvera.ai/v1/traces").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    ok = _try_upload_capture(
        endpoint="https://ingest.juvera.ai",
        api_key="jvr_test", org_id="org_test",
        payload={"spans": []},
    )
    assert ok is False


@respx.mock
def test_upload_success_returns_true():
    from juvera_sdk.local_relay import _try_upload_capture

    respx.post("https://ingest.juvera.ai/v1/traces").mock(
        return_value=httpx.Response(202, text="accepted")
    )
    ok = _try_upload_capture(
        endpoint="https://ingest.juvera.ai",
        api_key="jvr_test", org_id="org_test",
        payload={"spans": [{"id": "s1"}]},
    )
    assert ok is True


# --- Fix 3: _forward_to_ingest must not raise on upstream errors ---

def _make_relay_config(ingest_endpoint: str) -> "RelayConfig":
    from juvera_sdk.local_relay import RelayConfig
    return RelayConfig(
        host="127.0.0.1",
        port=4318,
        ingest_endpoint=ingest_endpoint,
        api_key="jvr_test",
        org_id="org_test",
    )


@respx.mock
def test_relay_returns_2xx_when_upload_fails_with_5xx():
    """_forward_to_ingest must not raise when ingest returns 500."""
    from juvera_sdk.local_relay import _forward_to_ingest

    respx.post("https://ingest.juvera.ai/v1/traces").mock(
        return_value=httpx.Response(500, text="server error")
    )
    cfg = _make_relay_config("https://ingest.juvera.ai")
    # Should not raise; returns a 2xx-equivalent status
    status, body = _forward_to_ingest(cfg, "/v1/traces", {"resourceSpans": []})
    assert status == 202
    assert body.get("accepted") is True


@respx.mock
def test_relay_returns_2xx_when_upload_fails_with_network_error():
    """_forward_to_ingest must not raise on ConnectError."""
    from juvera_sdk.local_relay import _forward_to_ingest

    respx.post("https://ingest.juvera.ai/v1/traces").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    cfg = _make_relay_config("https://ingest.juvera.ai")
    status, body = _forward_to_ingest(cfg, "/v1/traces", {"resourceSpans": []})
    assert status == 202
    assert body.get("accepted") is True
