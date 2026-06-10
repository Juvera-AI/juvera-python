"""Direct tests for the resolve_baseline() helper added in roi.py.

source ∈ {'default', 'override', 'unknown'} drives badge attribution
across display surfaces; this test pins its behavior.
"""
from __future__ import annotations

from juvera_sdk.roi import resolve_baseline, WORKFLOW_BASELINES


class _FakeConfig:
    """Stand-in for juvera_sdk._config — only needs .workflow_baselines."""
    def __init__(self, workflow_baselines):
        self.workflow_baselines = workflow_baselines


def test_default_source_when_workflow_in_global_and_no_config():
    baseline, source = resolve_baseline("ticket_deflection", config=None)
    assert source == "default"
    assert baseline == WORKFLOW_BASELINES["ticket_deflection"]


def test_default_source_when_config_has_no_override_for_workflow():
    config = _FakeConfig(workflow_baselines={"other_workflow": {"human_cost_usd": 1.0, "human_time_minutes": 1}})
    baseline, source = resolve_baseline("ticket_deflection", config=config)
    assert source == "default"
    assert baseline == WORKFLOW_BASELINES["ticket_deflection"]


def test_override_source_when_config_has_override_for_workflow():
    override = {"human_cost_usd": 12.0, "human_time_minutes": 8}
    config = _FakeConfig(workflow_baselines={"ticket_deflection": override})
    baseline, source = resolve_baseline("ticket_deflection", config=config)
    assert source == "override"
    assert baseline == override


def test_unknown_source_when_workflow_in_neither():
    baseline, source = resolve_baseline("not_a_real_workflow", config=None)
    assert source == "unknown"
    assert baseline == {}


def test_unknown_source_when_config_has_unrelated_overrides():
    config = _FakeConfig(workflow_baselines={"x": {"human_cost_usd": 1.0, "human_time_minutes": 1}})
    baseline, source = resolve_baseline("not_a_real_workflow", config=config)
    assert source == "unknown"
    assert baseline == {}


def test_handles_config_none_gracefully():
    baseline, source = resolve_baseline("ticket_deflection", config=None)
    assert source == "default"


def test_handles_config_with_no_workflow_baselines_attr():
    """When SDK init'd without workflow_baselines, config.workflow_baselines is None.
    Helper must treat that as no overrides."""
    class _NoOverrideConfig:
        workflow_baselines = None
    baseline, source = resolve_baseline("ticket_deflection", config=_NoOverrideConfig())
    assert source == "default"
