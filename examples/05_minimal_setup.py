"""Minimal Juvera setup — 6 lines of instrumentation.

Prerequisites:
    export JUVERA_API_KEY=jvr_...
    export JUVERA_ORG_ID=your-org-id
    export JUVERA_ENDPOINT=http://localhost:8001

    At least one provider SDK must be installed, with its API key set:
        pip install juvera-sdk anthropic && export ANTHROPIC_API_KEY=sk-ant-...
        pip install juvera-sdk openai && export OPENAI_API_KEY=sk-...
"""
import os
import sys
import juvera_sdk as j

# Import provider SDKs — at least one must be available
_API_ERRORS = []

try:
    import anthropic
    from anthropic import Anthropic
    _API_ERRORS.append(anthropic.APIError)
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import openai
    from openai import OpenAI
    _API_ERRORS.append(openai.APIError)
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

_API_ERRORS = tuple(_API_ERRORS)

if not HAS_ANTHROPIC and not HAS_OPENAI:
    sys.exit("Error: install at least one provider SDK: pip install anthropic  OR  pip install openai")

# 1. Init (reads JUVERA_API_KEY, JUVERA_ORG_ID from env)
j.init()

# 2. Wrap clients — auto-captures prompt, completion, tokens, model, and cost
claude = j.wrap_anthropic(Anthropic(), agent_id="triage_agent", default_workflow_type="ticket_deflection") if HAS_ANTHROPIC else None
gpt = j.wrap_openai(OpenAI(), agent_id="resolution_agent", default_workflow_type="ticket_deflection") if HAS_OPENAI else None


def _call_provider(client_fn):
    """Call a provider API, falling back gracefully on API errors."""
    try:
        return client_fn()
    except _API_ERRORS as e:
        print(f"  [skipped] Provider API error: {e.__class__.__name__}: {e}")
        return None


# 3. Decorate functions — one param
@j.agent("triage")
def classify(ticket: str):
    if claude:
        resp = _call_provider(lambda: claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": f"Classify this ticket: {ticket}"}],
        ))
        if resp is not None:
            return resp
    if gpt:
        resp = _call_provider(lambda: gpt.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=200,
            messages=[{"role": "user", "content": f"Classify this ticket: {ticket}"}],
        ))
        if resp is not None:
            return resp
    print("  [skipped] No working provider available for classify()")
    return None


@j.agent("resolver")
def resolve(ticket: str, triage: str):
    if gpt:
        resp = _call_provider(lambda: gpt.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=200,
            messages=[{"role": "user", "content": f"Draft response.\nTicket: {ticket}\nTriage: {triage}"}],
        ))
        if resp is not None:
            return resp
    if claude:
        resp = _call_provider(lambda: claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": f"Draft response.\nTicket: {ticket}\nTriage: {triage}"}],
        ))
        if resp is not None:
            return resp
    print("  [skipped] No working provider available for resolve()")
    return None


# 4. Use normally — everything auto-captured inside a workflow context
ticket = "Payment failed but I was charged twice. Need refund."
with j.workflow(work_item_id="wi_demo_001", workflow_type="ticket_deflection", agent_id="support_agent"):
    triage_resp = classify(ticket)
    triage_text = j.response_text(triage_resp) if triage_resp else "(no response — check provider API keys and billing)"
    print(f"Triage: {triage_text}")

    resolution_resp = resolve(ticket, triage_text)
    resolution_text = j.response_text(resolution_resp) if resolution_resp else "(no response — check provider API keys and billing)"
    print(f"Resolution: {resolution_text}")

# 5. Record business impact
j.impact("cost_reduction", 22.0, source="zendesk")

# 6. Done
j.flush()
print("Traces sent to Juvera.")
