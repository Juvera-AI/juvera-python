# juvera-sdk

Open instrumentation SDK for Juvera — emit agent telemetry and business-impact signals in under 10 minutes.

## Installation

```bash
pip install juvera-sdk
```

## Quickstart

```python
import juvera_sdk as j

j.init(
    api_key="jvr_your_key",
    org_id="org_your_org",
    service_name="my-agent",
)

with j.agent_span(agent_id="agent_01", work_item_id="wi_001") as span:
    span.set_model("claude-sonnet-4-6", provider="anthropic")
    span.set_tokens(input=400, output=150)
    # ... your agent logic ...

j.record_impact_signal(
    impact_type="cost_reduction",
    value=120.0,
    unit="seconds",
    work_item_id="wi_001",
    source_system="zendesk",
)

j.flush()
```

## The `work_item_id` concept

Every `agent_span()` is tied to a `work_item_id` — the unique identifier for one unit of agent work (e.g., a support ticket, a document, a task). This ID links spans to impact signals so Juvera can measure business outcomes per work item.

If you omit `work_item_id`, a UUID is generated automatically. Pass your own ID (e.g., a Zendesk ticket ID) to enable cross-system attribution.

## Debug mode

Set `endpoint="local"` to print spans and signals to stdout without making network calls:

```python
j.init(api_key="any", org_id="org_test", endpoint="local", debug=True)
```

## API Reference

| Function | Description |
|----------|-------------|
| `j.init(api_key, org_id, ...)` | Configure the SDK. Call once at startup. |
| `j.agent_span(agent_id, work_item_id, ...)` | Context manager wrapping one unit of agent work. Yields an `AgentSpan`. |
| `span.set_model(model, provider)` | Record which LLM model was used. |
| `span.set_tokens(input, output)` | Record token consumption. |
| `span.add_tool_call(tool_name, status)` | Record a tool/function call. |
| `span.set_error(error)` | Record an exception on the span. |
| `j.record_impact_signal(impact_type, value, ...)` | Emit a business outcome event. |
| `j.record_handoff(reason, reviewer_role)` | Record a human-in-the-loop handoff. |
| `j.flush()` | Force-export any buffered spans before process exit. |
| `j.shutdown()` | Shut down the SDK and release resources. |

## OSS scope

`juvera-sdk` is the open-source instrumentation layer. It answers *"how do I emit good data?"* and nothing more.

Attribution, benchmarking, compliance scoring, and the Juvera dashboard are all server-side and part of the Juvera platform — not this package.

What this SDK does:
- Wraps OpenTelemetry spans with Juvera-specific attributes
- Serialises spans to the Juvera wire format and POSTs to `/v1/traces`
- Sends `ImpactSignal` events to `/v1/impact-signals`
- Provides a `MockExporter` and `DebugExporter` for local development and testing

What this SDK does NOT do:
- Analyse or score your agent's performance
- Access any proprietary Juvera APIs beyond `/v1/traces` and `/v1/impact-signals`
- Require a running Juvera instance (`endpoint="local"` works offline)

Learn more at [juvera.ai](https://juvera.ai).
