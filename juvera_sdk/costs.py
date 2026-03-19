# juvera_sdk/costs.py

MODEL_COSTS_USD_PER_TOKEN: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6":       {"input": 3.00 / 1e6, "output": 15.00 / 1e6},
    "claude-opus-4-6":         {"input": 15.00 / 1e6, "output": 75.00 / 1e6},
    "claude-haiku-4-5-20251001": {"input": 0.25 / 1e6, "output": 1.25 / 1e6},
    "gpt-4o":                  {"input": 2.50 / 1e6, "output": 10.00 / 1e6},
    "gpt-4o-mini":             {"input": 0.15 / 1e6, "output":  0.60 / 1e6},
    "gemini-1.5-pro":          {"input": 3.50 / 1e6, "output": 10.50 / 1e6},
    "gemini-1.5-flash":        {"input": 0.075 / 1e6, "output": 0.30 / 1e6},
}


def compute_token_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    costs = MODEL_COSTS_USD_PER_TOKEN.get(model, {})
    return (input_tokens * costs.get("input", 0.0) +
            output_tokens * costs.get("output", 0.0))
