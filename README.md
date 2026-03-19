# juvera-python

Open instrumentation SDK for AI agent business-impact events.

```bash
pip install juvera-sdk
```

---

## What it is

`juvera-sdk` lets you instrument AI agents to emit **OTel-compatible traces** and **business-impact signals** to the Juvera ingest gateway. It answers one question: *how do I emit good data?* Nothing more.

---

## Quickstart

```python
import juvera_sdk as j

j.init(
    api_key="jvr_your_key",
    org_id="org_your_org",
    service_name="support-agent",
    domain="support",          # support | marketing | sales | custom
)

with j.agent_span(agent_id="agent_01", work_item_id="wi_ZD98765") as span:
    span.set_model("claude-sonnet-4-6", provider="anthropic")
    span.set_tokens(input=420, output=180)
    span.add_tool_call("lookup_order_status", status="success")
    # ... your agent logic ...

j.record_impact_signal(
    impact_type="cost_reduction",
    value=180.0,
    impact_category="ticket_deflection",
    source_system="zendesk",
)

j.flush()
```

**Debug mode** — no network calls, prints to stdout:

```python
j.init(api_key="any", org_id="org_test", endpoint="local")
```

---

## What Juvera Cloud computes from this data

Once traces and signals reach the ingest gateway, the Juvera platform handles:

- **ROI attribution** — which agent actions drove which business outcomes
- **Benchmarking** — agent performance over time, by domain and workflow type
- **Compliance scoring** — policy adherence, human-in-the-loop rate, escalation patterns
- **Root cause analysis** — why deflection rates dropped, which tool failures cost the most

None of this logic is in this package. It runs server-side.

---

## What this SDK does not include

- Attribution engine
- Benchmarking or evaluation
- Compliance rules or scoring
- Dashboard or analytics
- Any API beyond `/v1/traces` and `/v1/impact-signals`

This package has no dependency on any closed Juvera service. `endpoint="local"` works fully offline.

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

### `work_item_id`

Every `agent_span()` is tied to a `work_item_id` — the unique identifier for one unit of agent work (e.g. a Zendesk ticket ID, a document ID, a task ID). This links spans to impact signals so Juvera can attribute outcomes to specific work items.

If you omit it, a UUID is generated automatically. Pass your own system's ID to enable cross-system attribution.

---

## Examples

- [`examples/01_manual_instrumentation.py`](examples/01_manual_instrumentation.py) — core loop
- [`examples/02_openai_assistant.py`](examples/02_openai_assistant.py) — wrapping an OpenAI call
- [`examples/03_langchain_agent.py`](examples/03_langchain_agent.py) — LangChain agent pattern

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

Built by [Juvera](https://juvera.ai).
