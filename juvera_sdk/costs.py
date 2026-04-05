"""Token cost lookup backed by the shared repo pricing catalog."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def _catalog_path() -> Path:
    for base in Path(__file__).resolve().parents:
        candidate = base / "packages" / "schemas" / "pricing" / "model_pricing.json"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Could not locate packages/schemas/pricing/model_pricing.json")


@lru_cache(maxsize=1)
def _load_catalog() -> dict[str, Any]:
    return json.loads(_catalog_path().read_text())


@lru_cache(maxsize=1)
def _build_indexes() -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, tuple[str, str]], dict[str, float]]:
    catalog = _load_catalog()
    by_provider_model: dict[tuple[str, str], dict[str, Any]] = {}
    by_model: dict[str, tuple[str, str]] = {}
    default_rates = {
        "prompt": float(catalog["default"]["prompt_per_million"]),
        "completion": float(catalog["default"]["completion_per_million"]),
        "cache": float(catalog["default"]["cache_per_million"]),
        "reasoning": float(catalog["default"]["reasoning_per_million"]),
    }

    for item in catalog.get("models", []):
        provider = str(item["provider"]).strip().lower()
        model = str(item["model"]).strip().lower()
        rates = {
            "provider": provider,
            "model": model,
            "prompt": float(item["prompt_per_million"]),
            "completion": float(item["completion_per_million"]),
            "cache": float(item["cache_per_million"]),
            "reasoning": float(item["reasoning_per_million"]),
        }
        by_provider_model[(provider, model)] = rates
        by_model.setdefault(model, (provider, model))
        for alias in item.get("aliases", []):
            by_model.setdefault(str(alias).strip().lower(), (provider, model))
    return by_provider_model, by_model, default_rates


def resolve_model_pricing(model: str | None, provider: str | None = None) -> tuple[dict[str, float] | None, str | None, str]:
    """Resolve shared pricing for a model/provider pair.

    Returns `(rates, canonical_model, strategy)` where strategy is one of
    `catalog`, `provider_default`, `global_default`, or `missing`.
    """

    by_provider_model, by_model, default_rates = _build_indexes()
    normalized_model = (model or "").strip().lower()
    normalized_provider = (provider or "").strip().lower()

    if normalized_provider and normalized_model:
        direct = by_provider_model.get((normalized_provider, normalized_model))
        if direct:
            return direct, direct["model"], "catalog"
        mapped = by_model.get(normalized_model)
        if mapped and mapped[0] == normalized_provider:
            resolved = by_provider_model[mapped]
            return resolved, resolved["model"], "catalog"
        for (candidate_provider, candidate_model), rates in by_provider_model.items():
            if candidate_provider == normalized_provider and normalized_model.startswith(candidate_model):
                return rates, rates["model"], "catalog"
        return default_rates, normalized_model or None, "provider_default"

    if normalized_model:
        mapped = by_model.get(normalized_model)
        if mapped:
            resolved = by_provider_model[mapped]
            return resolved, resolved["model"], "catalog"
        for (_, candidate_model), rates in by_provider_model.items():
            if normalized_model.startswith(candidate_model):
                return rates, rates["model"], "catalog"
        return default_rates, normalized_model, "global_default"

    if normalized_provider:
        return default_rates, None, "provider_default"

    return None, None, "missing"


def estimate_token_cost_usd(
    *,
    model: str | None,
    provider: str | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_tokens: int = 0,
    reasoning_tokens: int = 0,
) -> tuple[float, str]:
    rates, _, strategy = resolve_model_pricing(model, provider=provider)
    if rates is None:
        return 0.0, "missing"
    total = (
        (input_tokens / 1_000_000) * rates["prompt"] +
        (output_tokens / 1_000_000) * rates["completion"] +
        (cache_tokens / 1_000_000) * rates["cache"] +
        (reasoning_tokens / 1_000_000) * rates["reasoning"]
    )
    return round(total, 6), strategy


def compute_token_cost_usd(model: str, input_tokens: int, output_tokens: int, provider: str | None = None) -> float:
    """Compute token cost using the shared pricing catalog."""
    cost, _ = estimate_token_cost_usd(
        model=model,
        provider=provider,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    return cost
