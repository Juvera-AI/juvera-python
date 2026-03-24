from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class JuveraConfig:
    api_key: str
    org_id: str
    endpoint: str = "https://ingest.juvera.ai"
    service_name: str = "juvera-agent"
    domain: str | None = None
    agent_id: str | None = None
    debug: bool = False
    human_reviewer_cost_per_hour_usd: float = 50.0
    workflow_baselines: dict | None = None

    def __post_init__(self):
        if not self.api_key:
            raise ValueError("api_key is required")
        if not self.org_id:
            raise ValueError("org_id is required")

    @property
    def is_local(self) -> bool:
        return self.endpoint == "local"

    @property
    def traces_url(self) -> str:
        return f"{self.endpoint.rstrip('/')}/v1/traces"

    @property
    def signals_url(self) -> str:
        return f"{self.endpoint.rstrip('/')}/v1/impact-signals"
