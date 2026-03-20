# juvera-python

Instrument AI agents to emit traces and business-impact signals.

```bash
pip install juvera-sdk
```

---

## 30-second quickstart

```python
import juvera_sdk as j

j.init(
    api_key="jvr_your_key",
    org_id="org_your_org",
    endpoint="local",        # prints locally, no network
    domain="support",
)

with j.agent_span(agent_id="support_agent", work_item_id="wi_ZD98765") as span:
    span.set_model("gpt-4.1-mini", provider="openai")
    span.set_tokens(input=420, output=180)
    span.add_tool_call("lookup_order_status", status="success")

    j.record_impact_signal(
        impact_type="cost_reduction",
        value=18.5,
        impact_category="ticket_deflection",
        source_system="zendesk",
    )

j.flush()
```

**What you'll see:**

```
[juvera-debug] SPAN name='agent.run' trace_id=33d4ba... agent_id=support_agent work_item_id=wi_ZD98765 attrs={...}
[juvera-debug] IMPACT_SIGNAL {"signalId": "...", "impact": {"impactType": "cost_reduction", ...}}
```

Run `python examples/01_manual_instrumentation.py` to try it end-to-end.

---

## Core concepts

### `agent_span` — one unit of work

Every instrumented agent action lives inside an `agent_span`. It maps to one trace in the Juvera platform.

```python
with j.agent_span(
    agent_id="support_agent",
    work_item_id="wi_ZD98765",   # your system's ID — ticket, doc, task
    workflow_type="ticket_deflection",
) as span:
    span.set_model("gpt-4.1-mini", provider="openai")
    span.set_tokens(input=420, output=180)
    span.add_tool_call("lookup_crm", status="success")
    span.set_error(exception)    # if something went wrong
```

### `work_item_id` — the linking key

`work_item_id` connects a span to its impact signals. Use your system's native ID (Zendesk ticket, Jira issue, document ID). If omitted, a UUID is generated — but you lose cross-system attribution.

### `record_impact_signal` — business outcomes

Call this **inside** an `agent_span` to automatically inherit trace context.

```python
with j.agent_span(agent_id="agent_01", work_item_id="wi_123") as span:
    ...
    j.record_impact_signal(
        impact_type="cost_reduction",   # or: time_saved, revenue, risk_avoided, ...
        value=180.0,
        impact_category="ticket_deflection",
        source_system="zendesk",
        properties={"baseline_minutes": 25, "actual_minutes": 3},
    )
```

### `record_handoff` — human-in-the-loop

Call this **inside** an `agent_span` so the handoff is linked to the same trace.

```python
with j.agent_span(agent_id="agent_01", work_item_id="wi_123") as span:
    ...
    j.record_handoff(reason="low_confidence", reviewer_role="tier2_support")
```

> **Gotcha:** Calling `record_handoff()` outside an active `agent_span` (or without an explicit `work_item_id`) emits the handoff on a new, disconnected trace. You'll see a warning if this happens.

---

## What gets emitted

### Trace span attributes

| Attribute | Set by |
|-----------|--------|
| `juvera.agent_id` | `agent_span(agent_id=...)` |
| `juvera.work_item_id` | `agent_span(work_item_id=...)` or auto-UUID |
| `juvera.domain` | `init(domain=...)` or `agent_span(domain=...)` |
| `juvera.workflow_type` | `agent_span(workflow_type=...)` |
| `gen_ai.request.model` | `span.set_model(...)` |
| `gen_ai.usage.input_tokens` | `span.set_tokens(input=...)` |
| `gen_ai.usage.output_tokens` | `span.set_tokens(output=...)` |

### Impact signal payload (abbreviated)

```json
{
  "signalId": "ae085c12-...",
  "agent": { "agentId": "support_agent", "orgId": "org_demo", "domain": "support" },
  "impact": {
    "impactType": "cost_reduction",
    "impactCategory": "ticket_deflection",
    "value": { "amount": 18.5, "currency": "USD", "direction": "positive" },
    "attribution": { "agentContribution": 1.0, "confidence": 0.8, "mode": "deterministic" },
    "properties": { "ticket_id": "ZD98765" }
  },
  "metadata": { "sourceSystem": "zendesk", "sourceEvent": "ticket_resolved" }
}
```

---

## Common patterns

### Support ticket deflection

```python
with j.agent_span(
    agent_id="support_deflection_agent",
    work_item_id=ticket_id,
    workflow_type="ticket_deflection",
) as span:
    span.set_model("gpt-4.1-mini", provider="openai")
    span.set_tokens(input=input_tokens, output=output_tokens)

    answer = deflect(ticket)

    j.record_impact_signal(
        impact_type="cost_reduction",
        value=22.0,
        impact_category="ticket_deflection",
        source_system="zendesk",
        properties={"ticket_id": ticket_id, "resolved": True},
    )
```

### Human-in-the-loop escalation

```python
with j.agent_span(agent_id="triage_agent", work_item_id=ticket_id) as span:
    if confidence < 0.7:
        j.record_handoff(reason="low_confidence", reviewer_role="tier2_support")
```

---

## API reference

| Call | Description |
|------|-------------|
| `j.init(api_key, org_id, ...)` | Configure once at startup |
| `j.agent_span(agent_id, work_item_id, ...)` | Context manager for one unit of work. Yields `AgentSpan`. |
| `span.set_model(model, provider)` | Record which LLM was used |
| `span.set_tokens(input, output)` | Record token consumption |
| `span.add_tool_call(name, status)` | Record a tool/function call |
| `span.set_error(exception)` | Mark span as errored |
| `j.record_impact_signal(impact_type, value, ...)` | Emit a business outcome event |
| `j.record_handoff(reason, reviewer_role)` | Record a human-in-the-loop handoff |
| `j.flush()` | Force-export buffered spans before process exit |
| `j.shutdown()` | Release resources |

**`init()` parameters**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `api_key` | required | Your Juvera API key |
| `org_id` | required | Your organisation ID |
| `endpoint` | `"https://ingest.juvera.ai"` | Use `"local"` for debug mode |
| `service_name` | `"juvera-agent"` | Identifies this service in traces |
| `domain` | `None` | `support`, `marketing`, `sales`, or `custom` |
| `agent_id` | `None` | Default agent ID (can be overridden per span) |
| `debug` | `False` | Extra logging |

---

## Common gotchas

**`endpoint="local"` — always start here.** It prints traces and signals to stdout with no network calls. Validate your payload structure before pointing at a real endpoint.

**`record_handoff()` must be inside an `agent_span`.** Calling it outside drops the trace context — the handoff emits on a new trace with no `work_item_id`. You'll get a `UserWarning` if this happens. Fix: move the call inside the `with agent_span(...)` block, or pass `work_item_id` explicitly.

**`agent_id` and `domain` can be set globally or per span.** Set them in `init()` as defaults, override in `agent_span()` for specific runs.

**`work_item_id` is your attribution key.** Without it, Juvera cannot link a span to an impact signal. Use your system's native ID wherever possible.

**Call `j.flush()` before process exit.** In batch/script contexts, spans may still be buffered. `flush()` guarantees they're exported.

---

## What this SDK does not include

- Attribution engine
- Benchmarking or evaluation
- Compliance rules or scoring
- Dashboard or analytics

This package has no dependency on any closed Juvera service. `endpoint="local"` works fully offline.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

Built by [Juvera](https://juvera.ai).
