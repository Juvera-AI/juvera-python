"""Regression guard: estimate_roi() after j.init() still respects custom baselines."""
import juvera_sdk as j


def test_custom_baseline_after_init():
    j.init(
        api_key="jvr_test",
        org_id="org_test",
        endpoint="local",
        debug=True,
        workflow_baselines={
            "internal_review": {"human_cost_usd": 60.0, "human_time_minutes": 40}
        },
    )
    try:
        roi = j.estimate_roi("internal_review", agent_cost_usd=0.50)
        assert roi["baseline_cost_usd"] == 60.0
        assert abs(roi["estimated_savings_usd"] - 59.5) < 0.001
    finally:
        j.shutdown()


def test_default_baseline_after_init_unchanged():
    j.init(api_key="jvr_test", org_id="org_test", endpoint="local", debug=True)
    try:
        roi = j.estimate_roi("ticket_deflection", agent_cost_usd=0.000175)
        assert roi["baseline_cost_usd"] == 22.0
    finally:
        j.shutdown()
