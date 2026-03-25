"""
support_v016_demo.py — Full v0.1.6 feature demo with real OpenAI calls.

Demonstrates: prompt/completion capture, context sources, custom events,
ROI estimation, human handoffs, and the debug run summary.

Usage:
    OPENAI_API_KEY=sk-... python examples/support_v016_demo.py
"""
from __future__ import annotations
import os
import time

import juvera_sdk as j

# ── Setup ────────────────────────────────────────────────────────────────────
openai_key = os.environ.get("OPENAI_API_KEY")
client = None
if openai_key:
    from openai import OpenAI
    client = OpenAI(api_key=openai_key)

model_name = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

j.init(
    api_key="jvr_demo",
    org_id="org_acme",
    endpoint="local",
    debug=True,
    domain="support",
    agent_id="support_v016",
    workflow_baselines={
        "vip_escalation": {"human_cost_usd": 45.0, "human_time_minutes": 30},
    },
)

# ── Ticket 1: Standard deflection (happy path) ──────────────────────────────
print("\n" + "─" * 60)
print("  TICKET 1: Standard support deflection")
print("─" * 60)

prompt_1 = "What is the refund policy for order #4100? It's been 12 days."

with j.agent_span(
    agent_id="support_v016",
    work_item_id="wi_ZD98765",
    workflow_type="ticket_deflection",
) as span:
    # Set prompt
    span.set_prompt(prompt_1)

    # Simulate RAG context retrieval
    span.add_context_source("refund_policy", doc_type="pdf", token_count=850)
    span.add_context_source("order_history", doc_type="api", token_count=320)
    j.record_event("retrieval", properties={"source": "vector_db", "chunks": "3"})

    # Call OpenAI (or simulate)
    if client:
        start = time.time()
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful support agent. Be empathetic and concise."},
                {"role": "user", "content": prompt_1},
            ],
        )
        reply = response.choices[0].message.content or ""
        span.set_model(model_name, provider="openai")
        if response.usage:
            span.set_tokens(input=response.usage.prompt_tokens, output=response.usage.completion_tokens)
    else:
        reply = "Our refund policy allows returns within 30 days of purchase. For order #4100, you're still within the window. I've initiated the refund process — you should see the credit within 3-5 business days."
        span.set_model(model_name, provider="openai")
        span.set_tokens(input=420, output=180)

    # Set completion
    span.set_completion(reply)

    # Tool calls
    span.add_tool_call("lookup_order", status="success", duration_ms=45)
    span.add_tool_call("check_refund_eligibility", status="success", duration_ms=12)

    # Guardrail check
    j.record_event("guardrail_check", status="success", properties={"rule": "pii_filter"})
    j.record_event("guardrail_check", status="success", properties={"rule": "tone_check"})

    # ROI estimation
    roi = j.estimate_roi(agent_cost_usd=0.002)
    print(f"\n  Reply: {reply[:100]}...")
    print(f"  ROI: ${roi['estimated_savings_usd']:.2f} savings (baseline: ${roi['baseline_cost_usd']:.2f})")

    # Impact signal
    j.record_impact_signal(
        impact_type="cost_reduction",
        value=18.5,
        impact_category="ticket_deflection",
        source_system="zendesk",
        source_event="ticket_resolved",
        properties={"ticket_id": "ZD98765", "work_item_id": "wi_ZD98765"},
    )

# ── Ticket 2: Low confidence → human handoff ────────────────────────────────
print("\n" + "─" * 60)
print("  TICKET 2: Low confidence → human handoff")
print("─" * 60)

prompt_2 = "I want to sue your company for selling me a defective product. My lawyer will be in touch."

with j.agent_span(
    agent_id="support_v016",
    work_item_id="wi_ZD98766",
    workflow_type="ticket_deflection",
) as span:
    span.set_prompt(prompt_2)

    # Call OpenAI (or simulate)
    if client:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a support triage agent. If the customer mentions legal action, escalate immediately."},
                {"role": "user", "content": prompt_2},
            ],
        )
        reply = response.choices[0].message.content or ""
        span.set_model(model_name, provider="openai")
        if response.usage:
            span.set_tokens(input=response.usage.prompt_tokens, output=response.usage.completion_tokens)
    else:
        reply = "I understand your frustration and take this very seriously. I'm escalating this to our legal team immediately."
        span.set_model(model_name, provider="openai")
        span.set_tokens(input=380, output=95)

    span.set_completion(reply)
    span.add_tool_call("sentiment_analysis", status="success", duration_ms=18)

    # Guardrail catches legal threat
    j.record_event("guardrail_check", status="failure", properties={"rule": "legal_threat_detector", "action": "escalate"})

    # Human handoff — low confidence, legal threat detected
    j.record_handoff(reason="legal_threat_detected", reviewer_role="legal_team")

    print(f"\n  Reply: {reply[:100]}...")
    print("  → Escalated to legal team (human handoff recorded)")

# ── Ticket 3: Tool failure + error handling ──────────────────────────────────
print("\n" + "─" * 60)
print("  TICKET 3: Tool failure scenario")
print("─" * 60)

prompt_3 = "Can you check the status of my order #9999?"

with j.agent_span(
    agent_id="support_v016",
    work_item_id="wi_ZD98767",
    workflow_type="ticket_deflection",
) as span:
    span.set_prompt(prompt_3)
    span.set_model(model_name, provider="openai")

    # Tool call fails
    span.add_tool_call("lookup_order", status="failure", duration_ms=5200, error="timeout: order service unavailable")

    # Cache hit for fallback response
    j.record_event("cache_hit", properties={"cache_key": "order_unavailable_template", "ttl": "300"})

    reply = "I'm sorry, our order tracking system is temporarily unavailable. Please try again in a few minutes, or contact us at support@example.com."
    span.set_completion(reply)
    span.set_tokens(input=85, output=42)

    # Record the error
    span.set_error(TimeoutError("order service unavailable"))

    print(f"\n  Reply: {reply[:100]}...")
    print("  → Tool failure recorded with error details")

# ── Ticket 4: Custom workflow baseline (VIP escalation) ─────────────────────
print("\n" + "─" * 60)
print("  TICKET 4: VIP escalation with custom baseline")
print("─" * 60)

with j.agent_span(
    agent_id="support_v016",
    work_item_id="wi_ZD98768",
    workflow_type="vip_escalation",
) as span:
    prompt_4 = "I'm a platinum member and I need priority support for my account issue."
    span.set_prompt(prompt_4)

    if client:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a VIP support agent. Provide premium, priority assistance."},
                {"role": "user", "content": prompt_4},
            ],
        )
        reply = response.choices[0].message.content or ""
        span.set_model(model_name, provider="openai")
        if response.usage:
            span.set_tokens(input=response.usage.prompt_tokens, output=response.usage.completion_tokens)
    else:
        reply = "Welcome, platinum member! I've prioritized your case and assigned a dedicated support specialist. Your account issue will be resolved within the hour."
        span.set_model(model_name, provider="openai")
        span.set_tokens(input=290, output=110)

    span.set_completion(reply)
    span.add_tool_call("check_membership_tier", status="success", duration_ms=8)
    span.add_context_source("vip_playbook", doc_type="markdown", token_count=450)

    roi = j.estimate_roi(agent_cost_usd=0.003)
    print(f"\n  Reply: {reply[:100]}...")
    print(f"  ROI (custom baseline): ${roi['estimated_savings_usd']:.2f} savings (baseline: ${roi['baseline_cost_usd']:.2f})")

# ── Flush and show summary ───────────────────────────────────────────────────
print("\n" + "─" * 60)
print("  FLUSHING — debug summary below")
print("─" * 60)
j.flush()

print(f"\njuvera-sdk v{j.__version__} demo complete.")
j.shutdown()
