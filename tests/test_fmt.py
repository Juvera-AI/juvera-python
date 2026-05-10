from juvera_sdk._fmt import fmt_cost, fmt_savings, fmt_pct


# ── fmt_cost ──────────────────────────────────────────────────────────────────

def test_fmt_cost_zero():
    assert fmt_cost(0) == "$0.00"
    assert fmt_cost(0.0) == "$0.00"
    assert fmt_cost(None) == "$0.00"


def test_fmt_cost_normal_amount_ceilings_up():
    """Cost rounds UP, not half-to-even — never under-report what was spent."""
    assert fmt_cost(0.04) == "$0.04"
    assert fmt_cost(0.0401) == "$0.05"  # ceiling, not 0.04
    assert fmt_cost(22.001) == "$22.01"
    assert fmt_cost(22.0) == "$22.00"


def test_fmt_cost_sub_cent_ceiling_two_sig_figs():
    """Sub-cent values: ceiling to 2 significant figures, fixed-point."""
    assert fmt_cost(0.000175) == "$0.00018"  # ceiling of 17.5 → 18
    assert fmt_cost(0.000174) == "$0.00018"  # ceiling of 17.4 → 18
    assert fmt_cost(0.000170001) == "$0.00018"  # ceiling — even tiny excess pushes up
    assert fmt_cost(0.000170) == "$0.00017"  # exact at 2 sig figs
    assert fmt_cost(0.000711) == "$0.00072"  # ceiling, not 0.00071
    assert fmt_cost(0.0002289) == "$0.00023"  # ceiling


def test_fmt_cost_no_scientific_notation():
    """Tiny values must not leak 'e-08' style notation."""
    assert "e-" not in fmt_cost(0.00000005).lower()
    assert "e-" not in fmt_cost(0.0000000001).lower()
    assert "e+" not in fmt_cost(1e10).lower()


def test_fmt_cost_thousands_separators():
    assert fmt_cost(1234.5) == "$1,234.50"
    assert fmt_cost(1234567.89) == "$1,234,567.89"  # ceiling: .89 → .89 (already exact)
    assert fmt_cost(1234567.891) == "$1,234,567.90"  # ceiling: .891 → .90


# ── fmt_savings ───────────────────────────────────────────────────────────────

def test_fmt_savings_floors_to_cents():
    """Savings should never overstate by rounding up to baseline."""
    assert fmt_savings(21.999825) == "+$21.99"  # floor, not 22.00
    assert fmt_savings(43.99963) == "+$43.99"
    assert fmt_savings(22.0) == "+$22.00"
    assert fmt_savings(0.0) == "+$0.00"
    assert fmt_savings(None) == "+$0.00"


def test_fmt_savings_negative():
    """Negative savings (regression) renders with '-'."""
    assert fmt_savings(-5.00) == "-$5.00"
    assert fmt_savings(-5.999) == "-$5.99"  # floor of absolute value
    assert fmt_savings(-0.0001) == "-$0.00"


def test_fmt_savings_thousands_separators():
    assert fmt_savings(1234.567) == "+$1,234.56"  # floor, not 1234.57
    # 1234567.89 is not exactly representable: floor lands at .88, not .89
    assert fmt_savings(1234567.89) == "+$1,234,567.88"
    assert fmt_savings(-9876.54) == "-$9,876.54"


# ── fmt_pct ───────────────────────────────────────────────────────────────────

def test_fmt_pct_floors_and_caps_at_99_99():
    assert fmt_pct(99.999) == "99.99%"  # floor, not 100.00
    assert fmt_pct(99.991) == "99.99%"
    assert fmt_pct(100.0) == "99.99%"  # capped — agents are never free
    assert fmt_pct(50.567) == "50.56%"  # floored
    assert fmt_pct(0.0) == "0.00%"
    assert fmt_pct(None) == "0.00%"


def test_fmt_pct_attribution_can_hit_100():
    """attribution_pct uses max_pct=100.0 because all-runs-attributed IS possible."""
    assert fmt_pct(100.0, max_pct=100.0) == "100.00%"
    assert fmt_pct(99.999, max_pct=100.0) == "99.99%"
    assert fmt_pct(50.567, max_pct=100.0) == "50.56%"
