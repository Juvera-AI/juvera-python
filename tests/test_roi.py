# tests/test_roi.py
import warnings
import pytest
import juvera_sdk as j
from juvera_sdk.exporters.mock import MockExporter


@pytest.fixture(autouse=True)
def sdk_init(mock_exporter):
    j.init(api_key="jvr_test", org_id="org_test", endpoint="local", _exporter=mock_exporter)
    yield mock_exporter
    j.shutdown()


def test_estimate_roi_basic(sdk_init):
    with j.agent_span(agent_id="a1", work_item_id="wi_001",
                       workflow_type="ticket_deflection"):
        roi = j.estimate_roi(agent_cost_usd=2.50)
    assert roi is not None
    assert roi["baseline_cost_usd"] == 22.0
    assert roi["agent_cost_usd"] == 2.50
    assert roi["estimated_savings_usd"] == 19.50
    assert roi["workflow_type"] == "ticket_deflection"


def test_estimate_roi_explicit_workflow(sdk_init):
    with j.agent_span(agent_id="a1", work_item_id="wi_001"):
        roi = j.estimate_roi(workflow_type="code_review", agent_cost_usd=5.0)
    assert roi["baseline_cost_usd"] == 95.0
    assert roi["estimated_savings_usd"] == 90.0


def test_estimate_roi_zero_agent_cost(sdk_init):
    with j.agent_span(agent_id="a1", work_item_id="wi_001",
                       workflow_type="ticket_deflection"):
        roi = j.estimate_roi()
    assert roi["agent_cost_usd"] == 0.0
    assert roi["estimated_savings_usd"] == 22.0


def test_estimate_roi_time_saved(sdk_init):
    with j.agent_span(agent_id="a1", work_item_id="wi_001",
                       workflow_type="document_review"):
        roi = j.estimate_roi(agent_cost_usd=15.0)
    assert roi["time_saved_minutes"] == 36.0


def test_estimate_roi_unknown_workflow_warns(sdk_init):
    with j.agent_span(agent_id="a1", work_item_id="wi_001",
                       workflow_type="unknown_type"):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            roi = j.estimate_roi()
    assert roi is None
    assert "No baseline found" in str(w[0].message)


def test_estimate_roi_no_workflow_warns(sdk_init):
    with j.agent_span(agent_id="a1", work_item_id="wi_001"):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            roi = j.estimate_roi()
    assert roi is None
    assert "could not determine workflow_type" in str(w[0].message)


def test_estimate_roi_custom_baselines(mock_exporter):
    j.init(api_key="jvr_test", org_id="org_test", endpoint="local",
           _exporter=mock_exporter,
           workflow_baselines={"custom_wf": {"human_cost_usd": 40.0, "human_time_minutes": 20}})
    with j.agent_span(agent_id="a1", work_item_id="wi_001",
                       workflow_type="custom_wf"):
        roi = j.estimate_roi(agent_cost_usd=5.0)
    assert roi["baseline_cost_usd"] == 40.0
    assert roi["estimated_savings_usd"] == 35.0
    j.shutdown()


def test_estimate_roi_from_set_work_item(sdk_init):
    j.set_work_item("wi_002", workflow_type="lead_qualification")
    with j.agent_span(agent_id="a1"):
        roi = j.estimate_roi(agent_cost_usd=3.0)
    j.clear_work_item()
    assert roi["baseline_cost_usd"] == 35.0
    assert roi["workflow_type"] == "lead_qualification"
