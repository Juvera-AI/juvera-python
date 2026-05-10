"""Test the fire-and-forget telemetry sender (Task 7.4)."""
import respx
import httpx
from juvera_sdk.telemetry import send_event


def test_send_no_op_when_endpoint_unset(tmp_path, monkeypatch):
    """No endpoint → sender returns False and does not POST."""
    monkeypatch.setenv("HOME", str(tmp_path))
    ok = send_event(command="demo", outcome="success", duration_ms=100, flags_used=[])
    assert ok is False


def test_send_no_op_when_telemetry_off(tmp_path, monkeypatch):
    """Even with an endpoint configured, opted-out users send nothing."""
    monkeypatch.setenv("HOME", str(tmp_path))
    from juvera_sdk.user_config import set_value
    # Don't set telemetry=true; just set endpoint
    set_value("telemetry_endpoint", "https://telemetry.test/v1/events")
    ok = send_event(command="demo", outcome="success", duration_ms=100, flags_used=[])
    assert ok is False


@respx.mock
def test_send_with_endpoint(tmp_path, monkeypatch):
    """With telemetry=true and endpoint set, send_event POSTs and returns True."""
    monkeypatch.setenv("HOME", str(tmp_path))
    from juvera_sdk.user_config import set_value
    set_value("telemetry", True)
    set_value("telemetry_endpoint", "https://telemetry.test/v1/events")

    route = respx.post("https://telemetry.test/v1/events").mock(
        return_value=httpx.Response(204)
    )

    ok = send_event(command="demo", outcome="success",
                    duration_ms=100, flags_used=["no_save"])
    assert ok is True
    assert route.called
    payload = route.calls.last.request.content.decode()
    assert "demo" in payload
    assert "no_save" in payload


@respx.mock
def test_send_swallows_network_errors(tmp_path, monkeypatch):
    """Network failures (connection, timeout, etc.) are swallowed; sender returns False."""
    monkeypatch.setenv("HOME", str(tmp_path))
    from juvera_sdk.user_config import set_value
    set_value("telemetry", True)
    set_value("telemetry_endpoint", "https://telemetry.test/v1/events")

    respx.post("https://telemetry.test/v1/events").mock(
        side_effect=httpx.ConnectError("boom")
    )
    ok = send_event(command="demo", outcome="success", duration_ms=1, flags_used=[])
    assert ok is False
