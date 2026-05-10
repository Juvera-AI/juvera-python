from juvera_sdk.demo import generate_synthetic_run, render_roi_card


def test_card_contains_key_fields():
    run = generate_synthetic_run(seed=1)
    out = render_roi_card(run, color=False, unicode=True)
    assert "ticket_deflection" in out
    assert "Human baseline" in out
    assert "$22.00" in out
    assert "Agent cost" in out
    assert "0.000175" in out or "0.0002" in out
    assert "Estimated value" in out
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
