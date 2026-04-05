import pytest
import juvera_sdk as j
from juvera_sdk.config import JuveraConfig


def test_config_requires_api_key():
    with pytest.raises(Exception):
        JuveraConfig(api_key="", org_id="org_x", endpoint="https://ingest.juvera.ai")


def test_config_local_endpoint():
    cfg = JuveraConfig(api_key="jvr_x", org_id="org_x", endpoint="local")
    assert cfg.is_local is True


def test_config_remote_endpoint():
    cfg = JuveraConfig(api_key="jvr_x", org_id="org_x", endpoint="https://ingest.juvera.ai")
    assert cfg.is_local is False
    assert cfg.traces_url == "https://ingest.juvera.ai/v1/traces"
    assert cfg.signals_url == "https://ingest.juvera.ai/v1/impact-signals"


def test_config_is_frozen():
    cfg = JuveraConfig(api_key="jvr_x", org_id="org_x", endpoint="local")
    with pytest.raises(Exception):
        cfg.api_key = "other"


def test_init_reads_env_when_explicit_args_omitted(mock_exporter, monkeypatch):
    monkeypatch.setenv("JUVERA_API_KEY", "jvr_env")
    monkeypatch.setenv("JUVERA_ORG_ID", "org_env")
    monkeypatch.setenv("JUVERA_ENDPOINT", "local")
    j.init(_exporter=mock_exporter)
    try:
        with j.agent_span(agent_id="agent_env", work_item_id="wi_env"):
            pass
        assert mock_exporter.span_count() == 1
    finally:
        j.shutdown()
