from juvera_sdk.costs import _catalog_path, compute_token_cost_usd


def test_catalog_path_resolves_in_package():
    """Catalog must be loadable from package-relative location (the wheel-install case)."""
    p = _catalog_path()
    assert p.is_file(), f"Catalog not found at {p}"
    assert p.name == "model_pricing.json"


def test_compute_cost_gpt_4o_mini_known_pricing():
    """Sanity check that the catalog actually loads and computes correctly."""
    cost = compute_token_cost_usd("gpt-4o-mini", 421, 187, provider="openai")
    # 421 * 0.15 / 1M + 187 * 0.60 / 1M = 0.000175
    assert 0.00015 < cost < 0.00020, cost
