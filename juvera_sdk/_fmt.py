"""Display-precision helpers for $ and % values shown to users.

Storage precision is unchanged (NDJSON keeps 6 decimals); these helpers
only affect rendered card / HTML / markdown output.

Direction discipline:
  - Cost ceilings UP (never under-report what was spent).
  - Savings floors DOWN (never overstate what was saved).
  - Percent floors DOWN AND caps at 99.99% (cost reduction can't be 100%).
  - Attribution % can hit 100% (override max_pct=100.0).
"""
from __future__ import annotations

import decimal
import math


def fmt_cost(v: float) -> str:
    """USD cost. Always rounds UP (ceiling). Thousands separators above $1k.

    - 0 (or None) → '$0.00'
    - >= $0.01 → ceiling to next cent, with thousands separators (e.g. $1,234.57)
    - 0 < v < $0.01 → ceiling at 2 significant figures, fixed-point notation
                      (no scientific notation; e.g. 0.000175 → '$0.00018')
    """
    if v is None or v == 0:
        return "$0.00"
    if abs(v) >= 0.01:
        ceiled = math.ceil(v * 100) / 100
        return f"${ceiled:,.2f}"
    # Sub-cent: ceiling to 2 significant figures.
    # Use Decimal to find the position of the first non-zero digit reliably.
    d = decimal.Decimal(repr(v)).normalize()
    # adjusted() returns the exponent when the number is in normalized scientific form
    # (e.g. 0.000175 → 1.75e-4 → adjusted = -4).
    exp = d.adjusted()
    sig_places = -exp + 1  # 2 sig figs → round to this many decimal places
    factor = 10 ** sig_places
    ceiled = math.ceil(v * factor) / factor
    return f"${ceiled:.{sig_places}f}"


def fmt_savings(v: float) -> str:
    """Savings rounded DOWN (floor) to cents. Thousands separators above $1k.

    Floor (not round) so the display never overstates by rounding up
    to the baseline value. Negative savings (cost overrun) get a leading '-'.
    """
    if v is None:
        return "+$0.00"
    if v < 0:
        floored = math.floor(abs(v) * 100) / 100
        return f"-${floored:,.2f}"
    floored = math.floor(v * 100) / 100
    return f"+${floored:,.2f}"


def fmt_pct(p: float, *, max_pct: float = 99.99) -> str:
    """Percent floored to 2 decimals, capped at max_pct (default 99.99).

    Why cap: '100.00% cost reduction' is misleading because agents always
    have some cost. Pass max_pct=100.0 for percentages that CAN legitimately
    hit 100 (e.g. attribution coverage).
    """
    if p is None:
        return "0.00%"
    floored = math.floor(p * 100) / 100
    return f"{min(floored, max_pct):.2f}%"
