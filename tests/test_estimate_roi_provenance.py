"""estimate_roi() must include provenance (confidence + source_url) in its return dict
for known workflow types. Backwards-compat: existing keys must still be present.
For unknown workflow_type, the function emits a warning and returns None (unchanged).
"""
from __future__ import annotations

import warnings

from juvera_sdk.roi import estimate_roi


def test_returns_confidence_and_source_url_for_known_workflow():
    result = estimate_roi("ticket_deflection", agent_cost_usd=0.5)
    assert result is not None
    assert "confidence" in result, "missing confidence key in estimate_roi return"
    assert "source_url" in result, "missing source_url key in estimate_roi return"
    assert result["confidence"] == "medium"
    assert result["source_url"] == "https://juvera.ai/baselines#ticket_deflection"


def test_existing_keys_still_present():
    """Backwards compat: no existing key removed or renamed."""
    result = estimate_roi("ticket_deflection", agent_cost_usd=0.5)
    assert result is not None
    for key in (
        "estimated_savings_usd",
        "baseline_cost_usd",
        "agent_cost_usd",
        "time_saved_minutes",
        "workflow_type",
    ):
        assert key in result, f"missing existing key {key!r}"


def test_unknown_workflow_returns_none_with_warning():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = estimate_roi("not_a_real_workflow", agent_cost_usd=0.5)
        assert result is None
        assert len(w) == 1
        assert "No baseline found" in str(w[0].message)


def test_no_workflow_returns_none_with_warning():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = estimate_roi(workflow_type=None, agent_cost_usd=0.5)
        assert result is None
        assert len(w) == 1
        assert "could not determine workflow_type" in str(w[0].message)


def test_custom_workflow_override_returns_none_source_url():
    """When a customer overrides via j.init(workflow_baselines={"internal_review": {...}})
    without providing source_url, estimate_roi() must return source_url=None — NOT a
    fabricated juvera.ai anchor that would 404. Same for confidence."""
    import juvera_sdk as j
    j.init(
        api_key="test",
        org_id="test",
        workflow_baselines={
            "internal_review": {
                "human_cost_usd": 60.0,
                "human_time_minutes": 40,
            }
        },
    )
    result = estimate_roi("internal_review", agent_cost_usd=1.0)
    assert result is not None
    assert result["baseline_cost_usd"] == 60.0
    assert result["confidence"] is None, (
        "custom override without confidence must return None, not 'low'"
    )
    assert result["source_url"] is None, (
        "custom override without source_url must return None, not a fabricated juvera.ai URL"
    )
