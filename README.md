# juvera-python

[![PyPI](https://img.shields.io/pypi/v/juvera-sdk)](https://pypi.org/project/juvera-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/juvera-sdk)](https://pypi.org/project/juvera-sdk/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Most observability tools tell you *how* your agent ran. Juvera tells you *what it was worth*.

```bash
pip install juvera-sdk==0.1.5
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

Run `python examples/local_debug.py` to validate the SDK locally with no network calls.

---

## Two happy paths

### Path A — local debug (no API key needed)

```python
j.init(api_key="any", org_id="org_demo", endpoint="local", domain="support")
```

Everything prints to stdout. Nothing leaves your machine. Use this to validate your payload shape before connecting to a real endpoint.

### Path B — real model call with OpenAI + local Juvera ingest

```python
import os
from openai import OpenAI
import juvera_sdk as j

j.init(
    api_key=os.environ["JUVERA_INGEST_API_KEY"],
    org_id="org_acme",
    endpoint=os.environ.get("JUVERA_INGEST_ENDPOINT", "http://localhost:8001"),
    domain="support",
)
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

j.record_impact_signal(
    impact_type="cost_reduction",
    value=18.5,
    impact_category="ticket_deflection",
    source_system="zendesk",
)
j.flush()
```

See `examples/support_roi.py` for the full version with fallback to local mode and configurable batch runs.

## Clean install verification

Validate the published package in a fresh environment:

```bash
python3 -m venv /tmp/juvera-sdk-verify
source /tmp/juvera-sdk-verify/bin/activate
pip install --upgrade pip
pip install juvera-sdk==0.1.5 openai
python -c "import juvera_sdk; print(juvera_sdk.__version__, juvera_sdk.__file__)"
```

Expected result:

- version prints `0.1.5`
- import path points into the virtualenv `site-packages`, not your repo checkout

## Real end-to-end test with OpenAI + local ingest

Start the local Juvera stack:

```bash
docker compose --profile app up -d --build
curl http://localhost:8001/health
```

Export the required credentials:

```bash
export OPENAI_API_KEY=sk-...
export JUVERA_INGEST_API_KEY=jvr_demo_key
export JUVERA_INGEST_ENDPOINT=http://localhost:8001
export JUVERA_EXAMPLE_RUNS=10
```

Run the example:

```bash
python examples/support_roi.py
```

Expected result:

- OpenAI returns real support replies
- the SDK emits one trace batch per run to `/v1/traces`
- the SDK emits one impact signal per run to `/v1/impact-signals`
- the script prints the processed tickets, total run count, and total impact value

If you want the fastest no-network proof first, run `python examples/local_debug.py`.

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

### `work_item_id` — the attribution join key

This is the most important concept in the SDK.

A `work_item_id` is a string you assign to one complete agent task — a support ticket, a sales opportunity, a compliance review. Every span and every impact signal that belongs to that task carries the same ID.

When your system of record resolves the outcome (Zendesk closes a ticket, Salesforce marks a deal won), that event arrives at Juvera with a `source_record_id`. The backend joins it to the `work_item_id` that was active during the agent session — and that's how ROI gets attributed.

**Without `work_item_id`:** you have traces.
**With `work_item_id`:** you have attributed ROI.

#### Where `work_item_id` appears in emitted payloads

| Signal type | Location | Key |
|-------------|----------|-----|
| Trace span | OTel span attribute | `juvera.work_item_id` |
| Impact signal | `impact.properties` | `work_item_id` |

The impact signal payload looks like:

```json
{
  "agent": { "agentId": "support_agent", "orgId": "org_acme" },
  "impact": {
    "impactType": "cost_reduction",
    "properties": {
      "work_item_id": "wi_ZD98765"
    }
  }
}
```

`work_item_id` is **not** in the `agent` block. The current gateway schema enforces `additionalProperties: false` on that block. A future release will promote `work_item_id` to a first-class context field (e.g. `context.workItemId`), but `impact.properties.work_item_id` is the correct and stable location in `0.1.x`.

```python
# Use your system's native ID — deterministic and debuggable
work_item_id = f"wi_{ticket_id}"       # "wi_ZD98765"
work_item_id = f"wi_opp_{opp_id}"     # "wi_opp_SF00123"

# Or let the SDK generate one and retrieve it:
with j.agent_span(agent_id="agent_01") as span:
    wi_id = span.work_item_id          # UUID if you didn't pass one
```

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

### Attach mode — add Juvera to existing telemetry

If you already use Phoenix, Langfuse, or raw OpenTelemetry, add Juvera as a span processor without changing your existing setup:

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

### Work item context for middleware

Set work item context at the top of the call stack — all downstream `agent_span()` calls automatically inherit it:

```python
import juvera_sdk as j

j.set_work_item("wi_ZD98765", workflow_type="ticket_deflection")
# ... agent spans created deeper in the call stack pick this up ...
j.clear_work_item()
```

FastAPI middleware example:

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

## Framework examples

### LangChain

```python
import juvera_sdk as j
j.init(api_key="jvr_...", org_id="org_acme", domain="support")

with j.agent_span(agent_id="lc_agent", work_item_id=f"wi_{ticket_id}") as span:
    result = agent_executor.invoke({"input": user_message})
    span.set_model("claude-sonnet-4-6", provider="anthropic")
    # extract token counts from LangChain callback or response metadata
```

### OpenAI

```python
import juvera_sdk as j
from openai import OpenAI

j.init(api_key="jvr_...", org_id="org_acme", domain="sales")
client = OpenAI()

with j.agent_span(agent_id="oai_agent", work_item_id=f"wi_opp_{opp_id}") as span:
    run = client.beta.threads.runs.create_and_poll(thread_id=tid, assistant_id=aid)
    span.set_model(run.model, provider="openai")
    if run.usage:
        span.set_tokens(input=run.usage.prompt_tokens, output=run.usage.completion_tokens)
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
| `JuveraSpanProcessor(api_key, org_id, ...)` | Attach-mode span processor for existing TracerProviders |
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

## Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | for live model calls | Auth for the OpenAI request in `examples/support_roi.py` |
| `JUVERA_INGEST_API_KEY` | for live Juvera ingest | Auth for `POST /v1/traces` and `POST /v1/impact-signals` |
| `JUVERA_INGEST_ENDPOINT` | optional | Defaults to `http://localhost:8001` for local testing |
| `JUVERA_ORG_ID` | optional | Defaults to `org_demo` in the example |
| `JUVERA_EXAMPLE_RUNS` | optional | Number of support tickets processed by `examples/support_roi.py` |

---

## Common gotchas

**`endpoint="local"` — always start here.** It prints traces and signals to stdout with no network calls. Validate your payload structure before pointing at a real endpoint.

**`debug=True` disables real HTTP emission.** Use it only for local validation. For real ingestion, leave `debug=False` and point `endpoint` at your Juvera gateway.

**`record_handoff()` must be inside an `agent_span`.** Calling it outside drops the trace context — the handoff emits on a new trace with no `work_item_id`. You'll get a `UserWarning` if this happens. Fix: move the call inside the `with agent_span(...)` block, or pass `work_item_id` explicitly.

**`agent_id` and `domain` can be set globally or per span.** Set them in `init()` as defaults, override in `agent_span()` for specific runs.

**`work_item_id` is your attribution key.** Without it, Juvera cannot link a span to an impact signal. Use your system's native ID wherever possible.

**Call `j.flush()` before process exit.** In batch/script contexts, spans may still be buffered. `flush()` guarantees they're exported.

**`agent_id=None` on handoff spans (v0.1.2 and earlier):** Fixed in v0.1.3. Handoff spans now inherit `juvera.agent_id` from the enclosing `agent_span` automatically.

**`work_item_id` location:** It lives in `impact.properties.work_item_id`, not `agent.workItemId`. The gateway schema enforces `additionalProperties: false` on the agent block — adding `workItemId` there causes a 422 error. The SDK places it correctly.

**Forgetting `j.flush()` in short-lived scripts:** In batch scripts or serverless functions, spans may still be buffered when the process exits. Always call `j.flush()` before shutdown.

---

## Known issues

**v0.1.0** (fixed in v0.1.1):

- `work_item_id` was silently dropped from the emitted ImpactSignal payload. Workaround: pass `properties={"work_item_id": "wi_..."}` manually.
- `debug=True` did not suppress HTTP in `record_impact_signal` — use `endpoint="local"` instead.
- `juvera_sdk.__version__` raised `AttributeError`.

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

