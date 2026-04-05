# juvera_sdk/costs.py
"""Token cost lookup for common LLM models. USD per token."""

# USD per token (not per 1K tokens)
MODEL_COSTS_USD_PER_TOKEN: dict[str, dict[str, float]] = {
    # Anthropic Claude 4
    "claude-sonnet-4-20250514":      {"input": 3.00 / 1e6, "output": 15.00 / 1e6},
    "claude-opus-4-20250514":        {"input": 15.00 / 1e6, "output": 75.00 / 1e6},
    # Anthropic Claude 3.5 / 3
    "claude-3-5-sonnet-20241022":    {"input": 3.00 / 1e6, "output": 15.00 / 1e6},
    "claude-3-haiku-20240307":       {"input": 0.25 / 1e6, "output": 1.25 / 1e6},
    "claude-haiku-4-5-20251001":     {"input": 0.25 / 1e6, "output": 1.25 / 1e6},
    # OpenAI
    "gpt-4o":                        {"input": 2.50 / 1e6, "output": 10.00 / 1e6},
    "gpt-4o-mini":                   {"input": 0.15 / 1e6, "output": 0.60 / 1e6},
    "gpt-4-turbo":                   {"input": 10.00 / 1e6, "output": 30.00 / 1e6},
    "gpt-4":                         {"input": 30.00 / 1e6, "output": 60.00 / 1e6},
    "gpt-3.5-turbo":                 {"input": 0.50 / 1e6, "output": 1.50 / 1e6},
    # Google
    "gemini-1.5-pro":                {"input": 3.50 / 1e6, "output": 10.50 / 1e6},
    "gemini-1.5-flash":              {"input": 0.075 / 1e6, "output": 0.30 / 1e6},
    "gemini-2.0-flash":              {"input": 0.10 / 1e6, "output": 0.40 / 1e6},
}

# Short aliases → canonical names
_MODEL_ALIASES: dict[str, str] = {
    "claude-sonnet-4-6": "claude-sonnet-4-20250514",
    "claude-opus-4-6": "claude-opus-4-20250514",
    "claude-sonnet": "claude-sonnet-4-20250514",
    "claude-opus": "claude-opus-4-20250514",
    "claude-haiku": "claude-haiku-4-5-20251001",
}

# Default cost for unknown models
_DEFAULT_COST = {"input": 2.00 / 1e6, "output": 8.00 / 1e6}


def compute_token_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Compute the USD cost for a given model and token counts."""
    resolved = _MODEL_ALIASES.get(model, model)
    costs = MODEL_COSTS_USD_PER_TOKEN.get(resolved, _DEFAULT_COST)
    return input_tokens * costs["input"] + output_tokens * costs["output"]
