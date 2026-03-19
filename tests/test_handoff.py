# tests/test_handoff.py
import juvera_sdk as j
import pytest
from juvera_sdk.exporters.mock import MockExporter


@pytest.fixture(autouse=True)
def sdk_init(mock_exporter):
    j.init(api_key="jvr_test", org_id="org_test", endpoint="local", _exporter=mock_exporter)
    yield mock_exporter
    j.shutdown()


def test_record_handoff_creates_span_with_human_required(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="agent_01", work_item_id="wi_005"):
        j.record_handoff(reason="low_confidence", reviewer_role="tier2_support")

    spans = exporter.all_spans()
    handoff_span = next((s for s in spans if s.name == "agent.handoff"), None)
    assert handoff_span is not None
    assert handoff_span.attributes["juvera.human_required"] is True
    assert handoff_span.attributes["juvera.handoff_reason"] == "low_confidence"
    assert handoff_span.attributes["juvera.reviewer_role"] == "tier2_support"
    assert handoff_span.attributes["juvera.work_item_id"] == "wi_005"


def test_record_handoff_sets_supervision_cost(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="agent_01", work_item_id="wi_006"):
        j.record_handoff(reason="escalation", reviewer_role="manager")

    spans = exporter.all_spans()
    handoff_span = next(s for s in spans if s.name == "agent.handoff")
    # 15 min at $50/hr = $12.50
    assert handoff_span.attributes["juvera.supervision_cost_usd"] == pytest.approx(12.5)
