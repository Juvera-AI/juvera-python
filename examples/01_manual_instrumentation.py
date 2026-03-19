"""
Example 01: Manual instrumentation — the core Juvera SDK loop.

Shows the minimal setup:
  1. j.init()      — configure once at startup
  2. agent_span()  — wrap one unit of agent work
  3. record_impact_signal() — emit a business outcome
  4. j.flush()     — ensure spans are exported before process exit
"""

import juvera_sdk as j

# ── 1. Initialise SDK ────────────────────────────────────────────────────────
j.init(
    api_key="jvr_demo_key",          # replace with your key
    org_id="org_acme",
    endpoint="local",                 # "local" → debug mode, prints to stdout
    service_name="support-agent",
    domain="support",
    agent_id="support_01",
    debug=True,
)

# ── 2. Instrument an agent run ────────────────────────────────────────────────
with j.agent_span(
    agent_id="support_01",
    work_item_id="wi_ZD98765",
    workflow_type="ticket_deflection",
) as span:
    # Record what model was used
    span.set_model("claude-sonnet-4-6", provider="anthropic")

    # Simulate doing work…
    answer = "Your order ships in 2-3 days."

    # Record tokens consumed
    span.set_tokens(input=420, output=180)

    # Record a tool that was called
    span.add_tool_call("lookup_order_status", status="success")

# ── 3. Record business impact ─────────────────────────────────────────────────
j.record_impact_signal(
    impact_type="cost_reduction",
    value=180.0,
    unit="seconds",          # time saved by deflecting the ticket
    work_item_id="wi_ZD98765",
    source_system="zendesk",
    impact_category="ticket_deflection",
)

# ── 4. Flush and exit ─────────────────────────────────────────────────────────
j.flush()
print(f"Done. Answer: {answer}")
