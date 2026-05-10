from juvera_sdk.demo import generate_synthetic_run, render_roi_card


def test_card_contains_key_fields():
    run = generate_synthetic_run(seed=1)
    out = render_roi_card(run, color=False, unicode=True)
    assert "ticket_deflection" in out
    assert "Human baseline" in out
    assert "$22.00" in out  # baseline is still normal cents
    assert "Agent cost" in out
    assert "$0.00018" in out  # ceiling, not 0.00017
    assert "Estimated value" in out
    assert "+$21.99" in out  # floored savings
    assert "99.99%" in out  # capped pct
    assert "Next: add work_item_id" in out


def test_card_uses_ascii_when_unicode_off():
    run = generate_synthetic_run(seed=1)
    out = render_roi_card(run, color=False, unicode=False)
    assert "┌" not in out and "│" not in out
    assert "+" in out  # ASCII frame uses '+'


def test_card_no_ansi_when_color_off():
    run = generate_synthetic_run(seed=1)
    out = render_roi_card(run, color=False, unicode=True)
    assert "\x1b[" not in out  # no ANSI escapes


def test_card_emits_ansi_when_color_on():
    run = generate_synthetic_run(seed=1)
    out = render_roi_card(run, color=True, unicode=True)
    assert "\x1b[" in out


def test_card_unicode_off_strips_arrow_and_dot():
    """When unicode=False, arrow and dot chars are also swapped to ASCII."""
    run = generate_synthetic_run(seed=1)
    out = render_roi_card(run, color=False, unicode=False)
    assert "→" not in out
    assert "·" not in out
    assert "->" in out  # ASCII arrow
    assert "-" in out   # ASCII dot (already in box, but should also be in body)


def test_card_uses_red_when_savings_negative():
    """Regression case: agent costs more than baseline; savings render in red."""
    run = generate_synthetic_run(seed=1)
    run["estimated_savings_usd"] = -5.00  # simulate cost overrun
    out = render_roi_card(run, color=True, unicode=True)
    assert "\x1b[31m" in out  # red ANSI
    assert "\x1b[32m" not in out  # not green


def test_card_uses_stored_savings_even_when_zero():
    """estimated_savings_usd=0.0 must be respected, not silently re-computed."""
    run = generate_synthetic_run(seed=1)
    run["estimated_savings_usd"] = 0.0
    out = render_roi_card(run, color=False, unicode=True)
    # Should display +$0.00 since stored value is 0.0
    assert "+$0.00" in out
