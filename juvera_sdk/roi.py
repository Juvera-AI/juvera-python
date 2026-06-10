# juvera_sdk/roi.py
from __future__ import annotations
import importlib
import warnings
from typing import TYPE_CHECKING, Any


from opentelemetry import trace as _trace
from juvera_sdk.costs import compute_token_cost_usd

if TYPE_CHECKING:
    from juvera_sdk.config import JuveraConfig


WORKFLOW_BASELINES: dict[str, dict[str, Any]] = {
    "ticket_deflection": {
        "human_cost_usd": 22.0,
        "human_cost_usd_range": [15.0, 32.0],
        "human_time_minutes": 15,
        "human_time_minutes_range": [10, 25],
        "confidence": "medium",
        "source_url": "https://juvera.ai/baselines#ticket_deflection",
        "last_reviewed": "2026-05-27",
    },
    "lead_qualification": {
        "human_cost_usd": 35.0,
        "human_cost_usd_range": [20.0, 60.0],
        "human_time_minutes": 25,
        "human_time_minutes_range": [10, 30],
        "confidence": "medium",
        "source_url": "https://juvera.ai/baselines#lead_qualification",
        "last_reviewed": "2026-05-27",
    },
    "document_review": {
        "human_cost_usd": 75.0,
        "human_cost_usd_range": [30.0, 140.0],
        "human_time_minutes": 45,
        "human_time_minutes_range": [30, 60],
        "confidence": "medium",
        "source_url": "https://juvera.ai/baselines#document_review",
        "last_reviewed": "2026-05-27",
    },
    "data_extraction": {
        "human_cost_usd": 18.0,
        "human_cost_usd_range": [5.0, 40.0],
        "human_time_minutes": 12,
        "human_time_minutes_range": [8, 23],
        "confidence": "medium",
        "source_url": "https://juvera.ai/baselines#data_extraction",
        "last_reviewed": "2026-05-27",
    },
    "code_review": {
        "human_cost_usd": 50.0,
        "human_cost_usd_range": [20.0, 95.0],
        "human_time_minutes": 30,
        "human_time_minutes_range": [20, 45],
        "confidence": "medium",
        "source_url": "https://juvera.ai/baselines#code_review",
        "last_reviewed": "2026-05-27",
    },
    "compliance_check": {
        "human_cost_usd": 120.0,
        "human_cost_usd_range": [50.0, 180.0],
        "human_time_minutes": 60,
        "human_time_minutes_range": [45, 90],
        "confidence": "medium",
        "source_url": "https://juvera.ai/baselines#compliance_check",
        "last_reviewed": "2026-05-27",
    },
    "content_generation": {
        "human_cost_usd": 50.0,
        "human_cost_usd_range": [20.0, 100.0],
        "human_time_minutes": 30,
        "human_time_minutes_range": [15, 75],
        "confidence": "medium",
        "source_url": "https://juvera.ai/baselines#content_generation",
        "last_reviewed": "2026-05-27",
    },
}


def resolve_baseline(
    workflow_type: str,
    config: "JuveraConfig | None",
) -> tuple[dict[str, Any], str]:
    """Return (baseline_dict, source) for a workflow_type, honoring overrides.

    source ∈ {'default', 'override', 'unknown'}.

    Used by estimate_roi() and by every display surface (demo render,
    processor print_summary) so badge attribution is consistent.
    A 'default' source means the baseline came from the SDK's documented
    WORKFLOW_BASELINES — methodology badge should render. 'override' means
    the customer supplied their own number via j.init(workflow_baselines=...) —
    Juvera does not certify these numbers, so badges suppress. 'unknown'
    means the workflow appears in neither — no row data.

    Pass config=None when called from a process that has no juvera_sdk._config
    (e.g. the `juvera report` CLI which renders persisted events from disk).
    """
    if config is not None and config.workflow_baselines and workflow_type in config.workflow_baselines:
        return config.workflow_baselines[workflow_type], "override"
    if workflow_type in WORKFLOW_BASELINES:
        return WORKFLOW_BASELINES[workflow_type], "default"
    return {}, "unknown"


def resolve_baseline_from_runtime(workflow_type: str) -> tuple[dict[str, Any], str]:
    """In-process convenience wrapper around resolve_baseline().

    Reads the current process's juvera_sdk._config (None if SDK wasn't
    initialized — e.g. tests that don't call j.init()) and forwards to
    resolve_baseline. Used by demo render, processor print_summary, and
    demo event creation so they share one override-resolution path.

    Do NOT use from cross-process callers (e.g. the `juvera report` CLI
    or local_relay.py) — they explicitly pass config=None to resolve_baseline
    to make the no-overrides expectation visible at the call site.
    """
    from juvera_sdk import _get_config  # lazy to avoid circular import
    try:
        config = _get_config()
    except RuntimeError:
        config = None
    return resolve_baseline(workflow_type, config)


def _auto_compute_agent_cost() -> float:
    """Read model + tokens from the current span and compute cost.

    Returns 0.0 if no active span or missing attributes.
    """
    span = _trace.get_current_span()
    if not span.is_recording():
        return 0.0
    # ReadableSpan isn't available yet (span still recording), but the
    # underlying Span object exposes attributes via the private _attributes dict.
    # We access via the public API where possible.
    attrs = getattr(span, "_attributes", None) or {}
    model = attrs.get("gen_ai.request.model")
    input_tokens = attrs.get("gen_ai.usage.input_tokens", 0)
    output_tokens = attrs.get("gen_ai.usage.output_tokens", 0)
    if model and (input_tokens or output_tokens):
        return compute_token_cost_usd(model, int(input_tokens), int(output_tokens))
    return 0.0


def estimate_roi(
    workflow_type: str | None = None,
    agent_cost_usd: float | None = None,
) -> dict[str, Any] | None:
    """Estimate ROI using workflow baselines.

    Works with or without j.init(). When uninitialized, uses default
    WORKFLOW_BASELINES and skips ContextVar-based workflow_type inference.
    Reads workflow_type from ContextVar only when an SDK config exists.
    Returns None with a warning if workflow_type is unknown or unresolvable.
    """
    from juvera_sdk import _get_config

    _ctx = importlib.import_module("juvera_sdk.context")

    # Tolerate uninitialized SDK: _get_config() raises RuntimeError when init() hasn't been called.
    try:
        config = _get_config()
    except RuntimeError:
        config = None

    if workflow_type is not None:
        eff_workflow_type = workflow_type
    elif config is not None:
        eff_workflow_type = _ctx.get_workflow_type()
    else:
        eff_workflow_type = None

    if eff_workflow_type is None:
        warnings.warn(
            "estimate_roi() could not determine workflow_type. "
            "Pass workflow_type explicitly or set it via agent_span() or set_work_item().",
            stacklevel=2,
        )
        return None

    baseline, baseline_source = resolve_baseline(eff_workflow_type, config)
    if baseline_source == "unknown":
        # Hint lists BOTH defaults and the user's overrides — preserves the
        # pre-refactor behavior that helped users spot typos like
        # `j.init(workflow_baselines={"internal_revue": ...})` followed by
        # `estimate_roi("internal_review")`.
        known_types = list(WORKFLOW_BASELINES.keys())
        if config is not None and config.workflow_baselines:
            known_types = sorted(set(known_types) | set(config.workflow_baselines.keys()))
        warnings.warn(
            f"No baseline found for workflow_type={eff_workflow_type!r}. "
            f"Known types: {known_types}. "
            f"Pass custom baselines via init(workflow_baselines={{...}}).",
            stacklevel=2,
        )
        return None

    baseline_cost = baseline["human_cost_usd"]
    baseline_time = baseline["human_time_minutes"]

    if agent_cost_usd is None:
        cost = _auto_compute_agent_cost()
    else:
        cost = agent_cost_usd
    savings = baseline_cost - cost
    time_saved = baseline_time * (savings / baseline_cost) if baseline_cost > 0 else 0.0

    return {
        "estimated_savings_usd": round(savings, 6),
        "baseline_cost_usd": baseline_cost,
        "agent_cost_usd": round(cost, 6),
        "time_saved_minutes": round(time_saved, 6),
        "workflow_type": eff_workflow_type,
        "confidence": baseline.get("confidence"),
        "source_url": baseline.get("source_url"),
        "baseline_source": baseline_source,
    }
