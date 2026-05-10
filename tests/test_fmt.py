from juvera_sdk._fmt import fmt_cost, fmt_savings, fmt_pct


def test_fmt_cost_zero():
    assert fmt_cost(0) == "$0.00"
    assert fmt_cost(0.0) == "$0.00"


def test_fmt_cost_normal_amount():
    assert fmt_cost(0.04) == "$0.04"
    assert fmt_cost(22.0) == "$22.00"
    assert fmt_cost(1.235) == "$1.24"  # standard 2-decimal rounding


def test_fmt_cost_sub_cent_preserves_precision():
    """Real gpt-4o-mini cost should not collapse to $0.00. Uses 2 sig figs."""
    assert fmt_cost(0.000175) == "$0.00017"  # 2 sig figs: 1,7
    assert fmt_cost(0.000711) == "$0.00071"  # 2 sig figs: 7,1
    assert fmt_cost(0.0002289) == "$0.00023"  # 2 sig figs: 2,3


def test_fmt_savings_floors_to_cents():
    """Savings should never overstate by rounding up to baseline."""
    assert fmt_savings(21.999825) == "+$21.99"
    assert fmt_savings(22.0) == "+$22.00"
    assert fmt_savings(0.0) == "+$0.00"
    assert fmt_savings(43.99963) == "+$43.99"


def test_fmt_pct_caps_at_99_99():
    """100% cost reduction is misleading; cap at 99.99%."""
    assert fmt_pct(99.999) == "99.99%"
    assert fmt_pct(100.0) == "99.99%"
    assert fmt_pct(50.567) == "50.56%"  # floored, not rounded
    assert fmt_pct(0.0) == "0.00%"


def test_fmt_pct_negative_or_low_unchanged():
    assert fmt_pct(0.01) == "0.01%"
    assert fmt_pct(50.0) == "50.00%"


def test_fmt_pct_custom_max():
    """Attribution coverage % can legitimately hit 100%."""
    assert fmt_pct(100.0, max_pct=100.0) == "100.00%"
    assert fmt_pct(99.999, max_pct=100.0) == "99.99%"
