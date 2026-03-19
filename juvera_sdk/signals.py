# juvera_sdk/signals.py
from __future__ import annotations
import httpx
from typing import Dict, Literal, Optional
from juvera_sdk.schema.impact_signal import ImpactSignal


def record_impact_signal(
    impact_type: str,
    value: float,
    impact_category: str = "general",
    agent_type: str = "llm",
    currency: str = "USD",
    direction: Literal["positive", "negative"] = "positive",
    agent_contribution: float = 1.0,
    confidence: float = 0.8,
    attribution_mode: str = "deterministic",
    domain: Optional[str] = None,
    source_system: Optional[str] = None,
    source_event: Optional[str] = None,
    properties: Optional[Dict] = None,
    # legacy kwargs accepted but ignored
    unit: Optional[str] = None,
    work_item_id: Optional[str] = None,
    source_record_id: Optional[str] = None,
    impact_category_alias: Optional[str] = None,
) -> None:
    """POST an ImpactSignal to the ingest gateway."""
    from juvera_sdk import _get_config

    config = _get_config()

    signal = ImpactSignal.build(
        org_id=config.org_id,
        agent_id=config.agent_id or "unknown",
        agent_type=agent_type,
        impact_type=impact_type,
        value=value,
        impact_category=impact_category,
        currency=currency,
        direction=direction,
        agent_contribution=agent_contribution,
        confidence=confidence,
        attribution_mode=attribution_mode,
        domain=domain or config.domain,
        source_system=source_system,
        source_event=source_event,
        properties=properties,
    )

    if config.is_local:
        import json
        print(f"[juvera-debug] IMPACT_SIGNAL {json.dumps(signal.model_dump(by_alias=True, exclude_none=True), default=str)}")
        return

    payload = signal.model_dump(by_alias=True, mode="json", exclude_none=True)
    resp = httpx.post(
        config.signals_url,
        json=payload,
        headers={"X-API-Key": config.api_key, "Content-Type": "application/json"},
        timeout=10.0,
    )
    resp.raise_for_status()
