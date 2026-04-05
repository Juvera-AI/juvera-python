"""Minimal Juvera setup — 6 lines of instrumentation.

Prerequisites:
    export JUVERA_API_KEY=jvr_...
    export JUVERA_ORG_ID=your-org-id
    export JUVERA_ENDPOINT=http://localhost:8001
    export ANTHROPIC_API_KEY=sk-ant-...
    export OPENAI_API_KEY=sk-...
    pip install juvera-sdk openai anthropic
"""
import os
import juvera_sdk as j
from anthropic import Anthropic
from openai import OpenAI

# 1. Init (reads JUVERA_API_KEY, JUVERA_ORG_ID from env)
j.init()

# 2. Wrap clients — auto-captures prompt, completion, tokens, model, and cost
claude = j.wrap_anthropic(Anthropic(), agent_id="triage_agent", default_workflow_type="ticket_deflection")
gpt = j.wrap_openai(OpenAI(), agent_id="resolution_agent", default_workflow_type="ticket_deflection")


# 3. Decorate functions — one param
@j.agent("triage")
def classify(ticket: str):
    return claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        messages=[{"role": "user", "content": f"Classify this ticket: {ticket}"}],
    )


@j.agent("resolver")
def resolve(ticket: str, triage: str):
    return gpt.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=200,
        messages=[{"role": "user", "content": f"Draft response.\nTicket: {ticket}\nTriage: {triage}"}],
    )


# 4. Use normally — everything auto-captured inside a workflow context
ticket = "Payment failed but I was charged twice. Need refund."
with j.workflow(work_item_id="wi_demo_001", workflow_type="ticket_deflection", agent_id="support_agent"):
    triage_resp = classify(ticket)
    triage_text = j.response_text(triage_resp)
    print(f"Triage: {triage_text}")

    resolution_resp = resolve(ticket, triage_text)
    resolution_text = j.response_text(resolution_resp)
    print(f"Resolution: {resolution_text}")

# 5. Record business impact
j.impact("cost_reduction", 22.0, source="zendesk")

# 6. Done
j.flush()
print("Traces sent to Juvera.")
