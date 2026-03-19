# juvera_sdk/schema/impact_signal.py
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict

IMPACT_TYPES = Literal[
    "revenue", "cost_reduction", "time_saved", "risk_avoided",
    "quality_improvement", "throughput_increase", "satisfaction_improvement",
]

DOMAIN_TYPES = Literal["support", "marketing", "sales", "custom"]


class ImpactValue(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    amount: float
    currency: str = "USD"
    direction: Literal["positive", "negative"] = "positive"


class ConfidenceBand(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    lower: float
    upper: float


class Attribution(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    agent_contribution: float = Field(alias="agentContribution", ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    mode: Literal["deterministic", "probabilistic", "experimental"] = "deterministic"
    confidence_band: ConfidenceBand = Field(alias="confidenceBand")


class AgentRef(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    agent_id: str = Field(alias="agentId")
    agent_type: str = Field(alias="agentType")
    org_id: Optional[str] = Field(default=None, alias="orgId")
    domain: Optional[DOMAIN_TYPES] = None


class ImpactBlock(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    impact_type: IMPACT_TYPES = Field(alias="impactType")
    impact_category: str = Field(alias="impactCategory")
    value: ImpactValue
    attribution: Attribution
    properties: Dict[str, Any] = Field(default_factory=dict)


class SignalMetadata(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    source_system: str = Field(alias="sourceSystem")
    source_event: Optional[str] = Field(default=None, alias="sourceEvent")
    mapping_rule_id: Optional[str] = Field(default=None, alias="mappingRuleId")


class ImpactSignal(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    signal_id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="signalId")
    schema_version: str = Field(default="1.0", alias="schemaVersion")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    agent: AgentRef
    impact: ImpactBlock
    metadata: Optional[SignalMetadata] = None

    @classmethod
    def build(
        cls,
        org_id: str,
        agent_id: str,
        impact_type: str,
        value: float,
        agent_type: str = "llm",
        impact_category: str = "general",
        currency: str = "USD",
        direction: Literal["positive", "negative"] = "positive",
        agent_contribution: float = 1.0,
        confidence: float = 0.8,
        attribution_mode: str = "deterministic",
        domain: Optional[str] = None,
        source_system: Optional[str] = None,
        source_event: Optional[str] = None,
        properties: Optional[Dict] = None,
        # deprecated kwargs silently ignored for back-compat
        unit: Optional[str] = None,
        work_item_id: Optional[str] = None,
        source_record_id: Optional[str] = None,
        impact_category_alias: Optional[str] = None,
    ) -> "ImpactSignal":
        return cls(
            agent=AgentRef(
                agentId=agent_id,
                agentType=agent_type,
                orgId=org_id,
                domain=domain,
            ),
            impact=ImpactBlock(
                impactType=impact_type,
                impactCategory=impact_category,
                value=ImpactValue(amount=value, currency=currency, direction=direction),
                attribution=Attribution(
                    agentContribution=agent_contribution,
                    confidence=confidence,
                    mode=attribution_mode,
                    confidenceBand=ConfidenceBand(
                        lower=max(0.0, confidence - 0.1),
                        upper=min(1.0, confidence + 0.1),
                    ),
                ),
                properties=properties or {},
            ),
            metadata=SignalMetadata(sourceSystem=source_system, sourceEvent=source_event)
            if source_system else None,
        )
