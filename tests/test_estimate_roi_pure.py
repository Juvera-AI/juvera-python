"""estimate_roi() must work with no j.init() and no ContextVar set."""
from juvera_sdk import estimate_roi


def test_works_with_explicit_workflow_and_cost():
    roi = estimate_roi("ticket_deflection", agent_cost_usd=0.000175)
    assert roi is not None
    assert roi["workflow_type"] == "ticket_deflection"
    assert roi["baseline_cost_usd"] == 22.0
    assert abs(roi["estimated_savings_usd"] - 21.999825) < 0.0001
    assert abs(roi["agent_cost_usd"] - 0.000175) < 0.0001


def test_returns_none_with_unknown_workflow():
    """Unknown workflow returns None and emits warning (existing behavior preserved)."""
    import warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = estimate_roi("not_a_real_workflow", agent_cost_usd=0.01)
    assert result is None
    assert any("not_a_real_workflow" in str(wi.message) for wi in w)


def test_returns_none_with_no_workflow_and_no_context():
    """Without explicit workflow_type and no ContextVar, returns None + warning."""
    import warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = estimate_roi(agent_cost_usd=0.01)
    assert result is None
    assert any("could not determine workflow_type" in str(wi.message).lower() for wi in w)
