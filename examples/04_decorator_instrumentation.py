"""Decorator-based Juvera instrumentation for direct provider SDK calls."""

from __future__ import annotations

import os

import anthropic
import juvera_sdk as j


j.init(
    api_key=os.environ["JUVERA_API_KEY"],
    org_id=os.environ["JUVERA_ORG_ID"],
    endpoint=os.environ.get("JUVERA_ENDPOINT", "local"),
    domain="support",
)

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


@j.anthropic_agent(
    "triage_agent",
    workflow_type="ticket_deflection",
    work_item_id="wi_{ticket.ticket_id}",
    prompt="prompt",
    tools=[j.tool_call("lookup_crm", duration_ms=45)],
)
def classify_ticket(prompt: str, ticket: dict[str, str], model: str = "claude-sonnet-4-20250514"):
    return client.messages.create(
        model=model,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )


ticket = {
    "ticket_id": "ZD-1001",
    "body": "My payment failed but I was charged twice.",
}

response = classify_ticket(
    prompt=f"Classify this ticket as JSON: {ticket['body']}",
    ticket=ticket,
)

print(j.response_text(response))
j.flush()
