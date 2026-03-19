# tests/test_signals.py
import respx
import httpx
import pytest
import juvera_sdk as j
from juvera_sdk.schema.impact_signal import ImpactSignal


@pytest.fixture(autouse=True)
def sdk_init():
    j.init(api_key="jvr_test", org_id="org_test", endpoint="https://ingest.example.com")
    yield
    j.shutdown()


def test_impact_signal_model_serialises_to_camel_case():
    sig = ImpactSignal.build(
        org_id="org_test",
        agent_id="agent_01",
        impact_type="cost_reduction",
        impact_category="ticket_deflection",
        value=180.0,
        unit="seconds",
        work_item_id="wi_001",
        source_system="zendesk",
    )
    d = sig.model_dump(by_alias=True)
    assert "signalId" in d
    assert d["agent"]["agentId"] == "agent_01"
    assert d["impact"]["impactType"] == "cost_reduction"
    assert d["impact"]["value"]["amount"] == 180.0


@respx.mock
def test_record_impact_signal_posts_to_ingest_gateway():
    route = respx.post("https://ingest.example.com/v1/impact-signals").mock(
        return_value=httpx.Response(200, json={"request_id": "req_1", "accepted_count": 1, "rejected_count": 0})
    )
    j.record_impact_signal(
        impact_type="cost_reduction",
        impact_category="ticket_deflection",
        value=180.0,
        unit="seconds",
        work_item_id="wi_001",
        source_system="zendesk",
    )
    assert route.called
    body = route.calls[0].request.content
    import json
    payload = json.loads(body)
    assert payload["impact"]["impactType"] == "cost_reduction"
    assert payload["agent"]["orgId"] == "org_test"
