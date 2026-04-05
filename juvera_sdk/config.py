from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class JuveraConfig:
    api_key: str
    org_id: str
    endpoint: str = "https://ingest.juvera.ai"
    service_name: str = "juvera-agent"
    domain: str | None = None
    agent_id: str | None = None
    environment: str = "prod"
    debug: bool = False
    human_reviewer_cost_per_hour_usd: float = 50.0
    workflow_baselines: dict | None = None

    def __post_init__(self):
        if not self.api_key:
            raise ValueError(
                "api_key is required. Pass it to j.init(api_key=...) or set JUVERA_API_KEY env var."
            )
        if not self.org_id:
            raise ValueError(
                "org_id is required. Pass it to j.init(org_id=...) or set JUVERA_ORG_ID env var."
            )

    @staticmethod
    def from_env(**overrides) -> JuveraConfig:
        """Create config from env vars + explicit overrides. Overrides take precedence."""
        return JuveraConfig(
            api_key=overrides.get("api_key") or os.environ.get("JUVERA_API_KEY", ""),
            org_id=overrides.get("org_id") or os.environ.get("JUVERA_ORG_ID", ""),
            endpoint=overrides.get("endpoint") or os.environ.get("JUVERA_ENDPOINT", "https://ingest.juvera.ai"),
            service_name=overrides.get("service_name") or os.environ.get("JUVERA_SERVICE_NAME", "juvera-agent"),
            domain=overrides.get("domain") or os.environ.get("JUVERA_DOMAIN"),
            agent_id=overrides.get("agent_id") or os.environ.get("JUVERA_AGENT_ID"),
            environment=overrides.get("environment") or os.environ.get("JUVERA_ENVIRONMENT", "prod"),
            debug=overrides.get("debug", os.environ.get("JUVERA_DEBUG", "").lower() in ("1", "true")),
            human_reviewer_cost_per_hour_usd=overrides.get("human_reviewer_cost_per_hour_usd", 50.0),
            workflow_baselines=overrides.get("workflow_baselines"),
        )

    @property
    def is_local(self) -> bool:
        return self.endpoint == "local"

    @property
    def traces_url(self) -> str:
        return f"{self.endpoint.rstrip('/')}/v1/traces"

    @property
    def signals_url(self) -> str:
        return f"{self.endpoint.rstrip('/')}/v1/impact-signals"
