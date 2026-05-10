"""Cloud upload errors must not crash the relay; capture continues."""
import respx
import httpx


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
