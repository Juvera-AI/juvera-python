"""Display-precision helpers for $ and % values shown to users.

Storage precision is unchanged (NDJSON keeps 6 decimals); these helpers
only affect rendered card / HTML / markdown output.
"""
from __future__ import annotations

import math


def fmt_cost(v: float) -> str:
    """Format a USD cost.

    - 0.0 → '$0.00'
    - >= $0.01 → '$X.XX' (cents, 2 decimal places)
    - < $0.01 → 2 significant figures (preserves precision for sub-cent agent costs)

    Examples:
      fmt_cost(0)         -> '$0.00'
      fmt_cost(0.000175)  -> '$0.00018'
      fmt_cost(0.000711)  -> '$0.00071'
      fmt_cost(0.0002289) -> '$0.00023'
      fmt_cost(0.04)      -> '$0.04'
      fmt_cost(22.0)      -> '$22.00'
    """
    if v is None:
        return "$0.00"
    if v == 0:
        return "$0.00"
    if abs(v) >= 0.01:
        return f"${v:.2f}"
    # Sub-cent: 2 significant figures.
    return f"${v:.2g}"


def fmt_savings(v: float) -> str:
    """Format estimated savings rounded DOWN (floor) to cents.

    Floor (not round) so the display never overstates by rounding up to
    the baseline value. Example: $21.999825 → '+$21.99' (not '+$22.00').
    Negative savings (cost overrun) are formatted with the leading '-'.
    """
    if v is None:
        return "+$0.00"
    if v < 0:
        return f"-${math.floor(abs(v) * 100) / 100:.2f}"
    return f"+${math.floor(v * 100) / 100:.2f}"


def fmt_pct(p: float, *, max_pct: float = 99.99) -> str:
    """Format a percentage floored to 2 decimals, capped at max_pct (default 99.99).

    Why cap: agents always have some cost, so '100.00% cost reduction'
    is misleading. We display 99.99% even when the floor lands at 100.
    """
    if p is None:
        return "0.00%"
    floored = math.floor(p * 100) / 100
    return f"{min(floored, max_pct):.2f}%"
