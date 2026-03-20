"""
local_debug.py — validate your instrumentation locally with no network calls.

Run:
    python examples/local_debug.py

Expected output: two SPAN lines and one IMPACT_SIGNAL line printed to stdout.
No API key or running gateway required.
"""

import juvera_sdk as j

j.init(
    api_key="demo_key",
    org_id="org_demo",
    endpoint="local",              # debug mode — prints to stdout, no network
    service_name="support-agent",
    domain="support",
    agent_id="support_deflection_agent",
    debug=True,
)

with j.agent_span(
    agent_id="support_deflection_agent",
    work_item_id="wi_ZD98765",
    workflow_type="ticket_deflection",
    business_unit="customer_support",
) as span:
    # Record what model you used
    span.set_model("gpt-4.1-mini", provider="openai")

    # Simulate doing work
    answer = "Your order ships in 2-3 business days."

    # Record token usage
    span.set_tokens(input=420, output=180)

    # Record tools called
    span.add_tool_call("lookup_order_status", status="success")

    # Attach any custom attribute
    span.set_attribute("juvera.ticket_id", "ZD98765")

    # Record a human handoff (inside the span = same trace)
    j.record_handoff(reason="refund_policy_exception", reviewer_role="tier2_support")

    # Record business impact (inside the span = linked to this work_item_id)
    j.record_impact_signal(
        impact_type="cost_reduction",
        value=18.5,
        impact_category="ticket_deflection",
        source_system="zendesk",
        source_event="ticket_resolved",
        properties={
            "ticket_id": "ZD98765",
            "baseline_resolution_minutes": 25,
            "actual_resolution_minutes": 3,
        },
    )

j.flush()
j.shutdown()

print(f"\nAnswer: {answer}")
print("\n✓ All spans and signals emitted. Point endpoint at your gateway to send for real.")
