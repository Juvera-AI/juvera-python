from juvera_sdk.demo import generate_synthetic_run


def test_default_run_is_ticket_deflection():
    run = generate_synthetic_run()
    assert run["workflow_type"] == "ticket_deflection"
    assert run["agent_id"]
    assert run["model"]
    assert run["input_tokens"] > 0
    assert run["output_tokens"] > 0
    assert len(run["tool_calls"]) >= 1


def test_seed_makes_run_deterministic():
    a = generate_synthetic_run(seed=42)
    b = generate_synthetic_run(seed=42)
    assert a == b


def test_workflow_flag_picks_baseline_present_run():
    run = generate_synthetic_run(workflow_type="lead_qualification", seed=1)
    assert run["workflow_type"] == "lead_qualification"


def test_unknown_workflow_falls_back_to_ticket_deflection_with_warning():
    import warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        run = generate_synthetic_run(workflow_type="not_real", seed=1)
    assert run["workflow_type"] == "ticket_deflection"
    assert any("not_real" in str(wi.message) for wi in w)


def test_known_baseline_no_scenario_falls_back_with_warning():
    """Workflow that's in WORKFLOW_BASELINES but not in _SCENARIOS still warns + falls back."""
    import warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        run = generate_synthetic_run(workflow_type="code_review", seed=1)
    assert run["workflow_type"] == "ticket_deflection"
    assert any("code_review" in str(wi.message) for wi in w)
    assert any("scenario" in str(wi.message).lower() for wi in w)
