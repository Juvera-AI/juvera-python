# tests/test_record_event.py
import warnings
import pytest
import juvera_sdk as j
from juvera_sdk.exporters.mock import MockExporter


@pytest.fixture(autouse=True)
def sdk_init(mock_exporter):
    j.init(api_key="jvr_test", org_id="org_test", endpoint="local", _exporter=mock_exporter)
    yield mock_exporter
    j.shutdown()


def test_record_event_basic(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="a1", work_item_id="wi_001"):
        j.record_event("guardrail_check", status="success")
    event = next(e for e in exporter.last_span().events if e.name == "guardrail_check")
    assert event.attributes["event.status"] == "success"


def test_record_event_with_properties(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="a1", work_item_id="wi_001"):
        j.record_event("cache_hit", properties={"cache_key": "user_123", "ttl": "300"})
    event = next(e for e in exporter.last_span().events if e.name == "cache_hit")
    assert event.attributes["event.cache_key"] == "user_123"
    assert event.attributes["event.ttl"] == "300"


def test_record_event_failure_status(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="a1", work_item_id="wi_001"):
        j.record_event("guardrail_check", status="failure",
                       properties={"rule": "pii_filter"})
    event = next(e for e in exporter.last_span().events if e.name == "guardrail_check")
    assert event.attributes["event.status"] == "failure"
    assert event.attributes["event.rule"] == "pii_filter"


def test_record_event_outside_span_warns(sdk_init):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        j.record_event("orphan_event")
    assert len(w) == 1
    assert "outside an active agent_span" in str(w[0].message)


def test_record_event_multiple_events(sdk_init):
    exporter = sdk_init
    with j.agent_span(agent_id="a1", work_item_id="wi_001"):
        j.record_event("retrieval", properties={"source": "vector_db"})
        j.record_event("guardrail_check", status="success")
    events = [e for e in exporter.last_span().events
              if e.name in ("retrieval", "guardrail_check")]
    assert len(events) == 2
