"""Per-command flag allowlist must never expose path/key values."""
import argparse

from juvera_sdk.telemetry import build_flags_used


def test_demo_no_save_present():
    ns = argparse.Namespace(no_save=True, workflow="ticket_deflection",
                             seed=None, live=False)
    assert build_flags_used("demo", ns) == ["no_save"]


def test_listen_api_key_value_never_emitted():
    ns = argparse.Namespace(api_key="jvr_SECRET_KEY",
                             org_id="org_secret",
                             local=False,
                             host="127.0.0.1", port=4318,
                             ingest_endpoint="https://ingest.juvera.ai",
                             api_base_url="http://localhost:8000",
                             setup_token=None, setup_id=None,
                             environment="local")
    flags = build_flags_used("listen", ns)
    serialized = " ".join(flags)
    assert "jvr_SECRET_KEY" not in serialized
    assert "org_secret" not in serialized
    assert "ingest.juvera.ai" not in serialized
    assert "cloud_set" in flags


def test_report_output_path_value_never_emitted():
    ns = argparse.Namespace(since="7d", source="all", format="html",
                             output="/home/me/secret/report.html", no_open=True)
    flags = build_flags_used("report", ns)
    serialized = " ".join(flags)
    assert "/home/me" not in serialized
    assert "secret" not in serialized
    assert "output_set" in flags


def test_unknown_flag_silently_excluded():
    """If a future flag is added without updating the allowlist, it's dropped."""
    ns = argparse.Namespace(no_save=True, brand_new_flag="leak_me", workflow="ticket_deflection",
                             seed=None, live=False)
    flags = build_flags_used("demo", ns)
    assert "brand_new_flag" not in flags
    assert "leak_me" not in " ".join(flags)


def test_unknown_command_returns_empty():
    """A future command without an allowlist entry returns no flags (defense in depth)."""
    ns = argparse.Namespace(some_flag=True, another="value")
    assert build_flags_used("future_command", ns) == []
