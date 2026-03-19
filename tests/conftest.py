# open-source/sdk-python/tests/conftest.py
import pytest
from juvera_sdk.config import JuveraConfig
from juvera_sdk.exporters.mock import MockExporter


@pytest.fixture
def mock_exporter() -> MockExporter:
    return MockExporter()


@pytest.fixture
def dev_config() -> JuveraConfig:
    return JuveraConfig(
        api_key="jvr_test_key",
        org_id="org_test",
        endpoint="local",
        service_name="test-agent",
        domain="support",
        debug=True,
    )
