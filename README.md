# juvera-python

[![PyPI](https://img.shields.io/pypi/v/juvera-sdk)](https://pypi.org/project/juvera-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/juvera-sdk)](https://pypi.org/project/juvera-sdk/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Most observability tools tell you *how* your agent ran. Juvera tells you *what it was worth*.

```bash
pip install juvera-sdk
```

---

## Quickstart

```python
import juvera_sdk as j

j.init(
    api_key="jvr_your_key",
    org_id="org_your_org",
    endpoint="local",        # prints locally, no network
    domain="support",
)

with j.agent_span(agent_id="support_agent", work_item_id="wi_ZD98765") as span:
    span.set_model("gpt-4o-mini", provider="openai")
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

`endpoint="local"` prints everything to stdout with no network calls. Switch to your Juvera gateway URL when ready for production.

---

## Core concepts

### `agent_span` — one unit of work

Every instrumented agent action lives inside an `agent_span`. It maps to one trace in the Juvera platform.

```python
with j.agent_span(
    agent_id="support_agent",
    work_item_id="wi_ZD98765",
    workflow_type="ticket_deflection",
) as span:
    span.set_model("gpt-4o-mini", provider="openai")
    span.set_tokens(input=420, output=180)
    span.add_tool_call("lookup_crm", status="success")
    span.set_error(exception)    # if something went wrong
```

### `work_item_id` — the attribution join key

A `work_item_id` ties an agent run to a business outcome. It's a string you assign to one complete task — a support ticket, a sales opportunity, a compliance review.

When your system of record resolves the outcome (Zendesk closes a ticket, Salesforce marks a deal won), that event arrives at Juvera with a `source_record_id`. The backend joins it to the `work_item_id` — and that's how ROI gets attributed.

**Without `work_item_id`:** you have traces. **With `work_item_id`:** you have attributed ROI.

```python
# Use your system's native ID
work_item_id = f"wi_{ticket_id}"       # "wi_ZD98765"
work_item_id = f"wi_opp_{opp_id}"     # "wi_opp_SF00123"

# Or let the SDK generate one
with j.agent_span(agent_id="agent_01") as span:
    wi_id = span.work_item_id          # UUID if you didn't pass one
```

`work_item_id` lives in `impact.properties.work_item_id` in emitted payloads — not in the `agent` block (the gateway schema enforces `additionalProperties: false` there).

### `record_impact_signal` — business outcomes

Call this **inside** an `agent_span` to automatically inherit trace context.

```python
j.record_impact_signal(
    impact_type="cost_reduction",   # or: time_saved, revenue, risk_avoided, ...
    value=180.0,
    impact_category="ticket_deflection",
    source_system="zendesk",
    properties={"baseline_minutes": 25, "actual_minutes": 3},
)
```

### `record_handoff` — human-in-the-loop

```python
with j.agent_span(agent_id="triage_agent", work_item_id=ticket_id) as span:
    if confidence < 0.7:
        j.record_handoff(reason="low_confidence", reviewer_role="tier2_support")
```

Must be called inside an `agent_span`. Calling it outside emits the handoff on a disconnected trace — the SDK warns if this happens.

---

## Attach mode

If you already use Phoenix, Langfuse, or raw OpenTelemetry, add Juvera as a span processor — no need to call `j.init()`:

```python
from opentelemetry.sdk.trace import TracerProvider
from juvera_sdk.processor import JuveraSpanProcessor

provider = TracerProvider(...)
provider.add_span_processor(JuveraSpanProcessor(
    api_key="jvr_...",
    org_id="org_acme",
))
# Your existing processors (Phoenix, Langfuse) stay as-is
```

`JuveraSpanProcessor` is also used internally by `j.init()` — one implementation, two entry points.

---

## Work item context for middleware

When `work_item_id` is known at the top of the call stack but `agent_span()` is called deep inside a library you don't control:

```python
j.set_work_item("wi_ZD98765", workflow_type="ticket_deflection")
# ... all agent_span() calls downstream inherit this ...
j.clear_work_item()
```

FastAPI example:

```python
@app.middleware("http")
async def track_work_item(request, call_next):
    work_item_id = request.headers.get("X-Work-Item-Id")
    if work_item_id:
        j.set_work_item(work_item_id)
    try:
        return await call_next(request)
    finally:
        j.clear_work_item()
```

Priority: explicit `agent_span(work_item_id=...)` > ContextVar from `set_work_item()` > auto-generated UUID.

---

## PII detection

In `debug` or `local` mode, the SDK scans span attributes for common PII patterns and prints warnings to stderr:

```
⚠ PII detected in span attribute 'gen_ai.output': email (confidence: high)
  Span: agent.run / trace_id: abc123
  Recommendation: review agent output filter before production
```

**Detected patterns:** email, US phone, SSN, credit card, API keys (`sk-`, `jvr_`, `ghp_`).

**Rules:**
- Warn only — never modifies span data, never blocks execution
- Only runs in debug/local mode, never in production
- Scans string attributes only, skips numbers and sequences
- Disable in attach mode with `JuveraSpanProcessor(pii_check=False)`

The fix for PII belongs in your agent's prompt or output filter, not in the telemetry layer. Server-side Presidio handles production redaction.

---

## Framework examples

### OpenAI

```python
import juvera_sdk as j
from openai import OpenAI

j.init(api_key="jvr_...", org_id="org_acme", domain="support")
client = OpenAI()

with j.agent_span(agent_id="support_agent", work_item_id=f"wi_{ticket_id}") as span:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": ticket_text}],
    )
    span.set_model("gpt-4o-mini", provider="openai")
    if response.usage:
        span.set_tokens(input=response.usage.prompt_tokens,
                        output=response.usage.completion_tokens)
```

### Anthropic

```python
import juvera_sdk as j
import anthropic

j.init(api_key="jvr_...", org_id="org_acme", domain="legal")
client = anthropic.Anthropic()

with j.agent_span(agent_id="claude_agent", work_item_id=f"wi_{doc_id}") as span:
    msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=1024,
                                  messages=[{"role": "user", "content": text}])
    span.set_model("claude-sonnet-4-6", provider="anthropic")
    span.set_tokens(input=msg.usage.input_tokens, output=msg.usage.output_tokens)
```

### LangChain

```python
import juvera_sdk as j
j.init(api_key="jvr_...", org_id="org_acme", domain="support")

with j.agent_span(agent_id="lc_agent", work_item_id=f"wi_{ticket_id}") as span:
    result = agent_executor.invoke({"input": user_message})
    span.set_model("claude-sonnet-4-6", provider="anthropic")
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
| `j.set_work_item(work_item_id, workflow_type)` | Set work item context for downstream spans |
| `j.clear_work_item()` | Clear work item context |
| `j.flush()` | Force-export buffered spans before process exit |
| `j.shutdown()` | Release resources |

**`init()` parameters**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `api_key` | required | Your Juvera API key |
| `org_id` | required | Your organisation ID |
| `endpoint` | `"https://ingest.juvera.ai"` | Use `"local"` for debug mode |
| `service_name` | `"juvera-agent"` | Service name in traces |
| `domain` | `None` | `support`, `marketing`, `sales`, or `custom` |
| `agent_id` | `None` | Default agent ID (overridable per span) |
| `debug` | `False` | Enable debug output and PII scanning |

**`JuveraSpanProcessor` parameters**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `api_key` | required | Your Juvera API key |
| `org_id` | required | Your organisation ID |
| `endpoint` | `"https://ingest.juvera.ai"` | Use `"local"` for debug mode |
| `debug` | `False` | Enable debug output and PII scanning |
| `domain` | `None` | Default domain |
| `pii_check` | `True` | Enable PII detection (only active in debug/local mode) |

---

## Gotchas

**Call `j.flush()` before process exit.** In batch scripts or serverless functions, spans may still be buffered.

**`record_handoff()` and `record_impact_signal()` should be called inside an `agent_span`.** Outside a span, they emit on disconnected traces with no `work_item_id`.

**`work_item_id` goes in `impact.properties`, not `agent`.** The gateway schema enforces `additionalProperties: false` on the agent block. The SDK places it correctly — don't override manually.

**`debug=True` suppresses real HTTP.** Use it for local validation only. For production, set `debug=False` and point `endpoint` at your gateway.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
