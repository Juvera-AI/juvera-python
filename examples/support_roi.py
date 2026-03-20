"""
support_roi.py — instrument a real OpenAI call and emit an impact signal.

Run in local debug mode (no Juvera API key needed):
    python examples/support_roi.py

For production use, set:
    JUVERA_API_KEY=jvr_...
    OPENAI_API_KEY=sk-...
    JUVERA_ENDPOINT=https://ingest.juvera.ai
"""
from __future__ import annotations
import os

# ── Juvera SDK setup ──────────────────────────────────────────────────────────
import juvera_sdk as juvera

juvera.init(
    api_key=os.environ.get("JUVERA_API_KEY", "demo_key"),
    org_id=os.environ.get("JUVERA_ORG_ID", "org_demo"),
    endpoint=os.environ.get("JUVERA_ENDPOINT", "local"),  # "local" = stdout, no network
    service_name="support-agent",
    domain="support",
    agent_id="support_deflection_agent",
    debug=True,
)

# ── Simulated or real ticket ──────────────────────────────────────────────────
ticket_id = "ZD98765"
ticket_text = "My order hasn't arrived yet. It's been 10 days."
work_item_id = f"wi_{ticket_id}"

# ── Agent span wraps the full agent session ───────────────────────────────────
with juvera.agent_span(
    agent_id="support_deflection_agent",
    work_item_id=work_item_id,
    workflow_type="ticket_deflection",
) as span:

    openai_api_key = os.environ.get("OPENAI_API_KEY")

    if openai_api_key:
        # Real OpenAI call (uses the standard chat completions API)
        from openai import OpenAI
        client = OpenAI(api_key=openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"Write a short, empathetic support reply: {ticket_text}"}],
        )
        reply = response.choices[0].message.content or ""
        span.set_model("gpt-4o-mini", provider="openai")
        span.set_tokens(
            input=response.usage.prompt_tokens,
            output=response.usage.completion_tokens,
        )
    else:
        # Simulated response for local testing
        reply = "Thanks for reaching out! Your order is on its way and should arrive within 2 business days."
        span.set_model("gpt-4o-mini", provider="openai")
        span.set_tokens(input=42, output=28)

    span.add_tool_call("lookup_order_status", status="success")

    # Record business impact — ticket deflected, no human needed
    juvera.record_impact_signal(
        impact_type="cost_reduction",
        value=18.5,
        impact_category="ticket_deflection",
        source_system="zendesk",
        source_event="ticket_resolved",
        properties={
            "ticket_id": ticket_id,
            "reply_preview": reply[:120],
        },
    )

juvera.flush()
juvera.shutdown()

print(f"\nReply: {reply}")
print("\n✓ Span + impact signal emitted. Set JUVERA_ENDPOINT to send to a real gateway.")
