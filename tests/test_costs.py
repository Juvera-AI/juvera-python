import pytest
from juvera_sdk.costs import compute_token_cost_usd


def test_compute_cost_claude_sonnet():
    # claude-sonnet-4-6: $3/M input, $15/M output
    cost = compute_token_cost_usd("claude-sonnet-4-6", input_tokens=1_000_000, output_tokens=0)
    assert cost == pytest.approx(3.0)


def test_compute_cost_unknown_model_returns_zero():
    cost = compute_token_cost_usd("unknown-model", input_tokens=1000, output_tokens=1000)
    assert cost == 0.0


def test_compute_cost_mixed():
    cost = compute_token_cost_usd("gpt-4o", input_tokens=500_000, output_tokens=250_000)
    assert cost == pytest.approx(500_000 * 2.50/1e6 + 250_000 * 10.00/1e6)
