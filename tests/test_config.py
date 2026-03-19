import pytest
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
