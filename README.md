# juvera-python

[![PyPI](https://img.shields.io/pypi/v/juvera-sdk)](https://pypi.org/project/juvera-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/juvera-sdk)](https://pypi.org/project/juvera-sdk/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Most observability tools tell you *how* your agent ran. Juvera tells you *what it was worth*.

## 60 seconds

```bash
pip install juvera-sdk
juvera demo
```

You'll see:

```
┌─────────────────────────────────────────────────────────────┐
│ Juvera captured 1 agent run                                 │
│ Workflow:        ticket_deflection                          │
│ Human baseline:  $22.00 · 15 min                            │
│ Agent cost:      $0.00018                                   │
│ Estimated value: +$21.99  (99.99% cost reduction)           │
└─────────────────────────────────────────────────────────────┘
```

No account. No API key. No data leaves your machine.

> **macOS Homebrew Python users:** `pip install` may hit a PEP 668 "externally-managed-environment" error. Use a venv: `python3 -m venv .venv && source .venv/bin/activate && pip install juvera-sdk && juvera demo`.

## Capture your real agent (2 more minutes)

```bash
juvera listen
export OPENAI_BASE_URL=http://127.0.0.1:4318/proxy/openai/v1
# run your agent normally — captures land in ~/.juvera/captures/

juvera report  # opens an HTML ROI report in your browser
```

## Use the ROI calculator standalone

```python
from juvera_sdk import estimate_roi
roi = estimate_roi("ticket_deflection", agent_cost_usd=0.0002)
# → {'estimated_savings_usd': 21.9998, ...}
```

## Configure

```bash
juvera config get                    # see all settings
juvera config set telemetry true     # opt in to anonymous usage stats (off by default)
```

## Privacy & telemetry

- Telemetry is **opt-in**. The first time you run any command other than `juvera config`, a one-line consent prompt appears **after** the command's primary output (so the ROI card is what you see first). Default = no; press Enter to decline.
- `juvera config` commands never trigger the consent prompt, and they never overwrite the value you just set.
- When opted in, telemetry sends: SDK version, OS/arch, command name, success/failure, duration, and **allowlisted flag names only** (e.g. presence of `--no-save`; the *value* of `--api-key`, `--output`, `--workflow`, etc. is never sent).
- Telemetry NEVER sends: prompts, completions, file paths, API keys, flag values, costs, workflow types, or any data from `~/.juvera/captures/`.
- Local metrics counters at `~/.juvera/metrics.json` are always-on but never leave your machine unless you opt in.
- Change your mind anytime: `juvera config set telemetry false` (or `true`).
- Schema: https://juvera.ai/telemetry-schema *(published when AWS infra lands; see issue #98)*.

---

## Detailed quickstart

### 2. Upgrade to workflow-first instrumentation

```python
import juvera_sdk as j
from openai import OpenAI

j.init(
    endpoint="http://127.0.0.1:4318",
    domain="support",
)

client = j.wrap_openai(
    OpenAI(),
    agent_id="support_agent",
    default_workflow_type="ticket_deflection",
)

with j.workflow(
    work_item_id="wi_ZD98765",
    workflow_type="ticket_deflection",
    agent_id="support_agent",
):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "What is the refund policy?"}],
    )

j.flush()
```

`j.workflow(...)` is the preferred top-level API. It keeps the episode story consistent while wrappers and framework instrumentors fill in prompt, completion, model, provider, and tokens automatically.

### Less boilerplate with decorators

If manual `span.set_prompt()` / `span.set_tokens()` calls feel too heavy, wrap your provider call once and let Juvera extract the common fields from the response:

```python
import juvera_sdk as j

@j.anthropic_agent(
    "triage_agent",
    workflow_type="ticket_deflection",
    work_item_id="wi_{ticket.ticket_id}",
    prompt="prompt",
    tools=[j.tool_call("lookup_crm", duration_ms=45)],
)
def classify_ticket(prompt, ticket, model="claude-sonnet-4-6"):
    return claude.messages.create(
        model=model,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

response = classify_ticket(
    prompt=f"Classify this ticket: {ticket['body']}",
    ticket=ticket,
)
triage_text = j.response_text(response)
```

Built-in decorators:

- `@j.openai_agent(...)` extracts model, completion, and token usage from OpenAI responses
- `@j.anthropic_agent(...)` does the same for Anthropic Messages responses
- `@j.instrument(...)` is the provider-agnostic escape hatch when you want a custom parser

### Workflow and context helpers

```python
with j.context(user_id="u_123", session_id="sess_abc", subject_key="customer_42"):
    with j.workflow(work_item_id="wi_ZD98765", workflow_type="ticket_deflection", agent_id="support_agent"):
        ...
```

You can also set long-lived request context with `j.set_context(...)` / `j.clear_context()`.

---

## Juvera Local Relay

For onboarding, Juvera can now sit in front of your app on loopback and prove it sees real traffic before your instrumentation is perfect.

### Start the relay

```bash
# Default — local capture only, no account needed
juvera listen
# Captures land in ~/.juvera/captures/<date>/

# With cloud upload — pass an API key (or set JUVERA_API_KEY in env)
juvera listen --api-key "$JUVERA_API_KEY" --org-id "$JUVERA_ORG_ID"

# Onboarding flow — setup token (uploads via X-Setup-Token)
juvera listen --setup-token "$JUVERA_SETUP_TOKEN" --setup-id "$JUVERA_SETUP_ID"

# Force local-only even when env credentials are set
juvera listen --local
```

The relay's mandatory startup banner shows the active mode:
- `LOCAL CAPTURE ONLY` — no upload (default, or `--local`)
- `LOCAL + CLOUD UPLOAD` — also uploads to `ingest.juvera.ai`

The relay exposes:

- `http://127.0.0.1:4318/v1/traces` for SDK or OTel attach mode
- `http://127.0.0.1:4318/proxy/openai/v1` for OpenAI smoke-test capture
- `http://127.0.0.1:4318/proxy/anthropic/v1` for Anthropic smoke-test capture
- `http://127.0.0.1:4318/status` for setup validation

### Proxy mode

No code changes required if your client supports a base URL override:

```bash
export OPENAI_BASE_URL=http://127.0.0.1:4318/proxy/openai/v1
export ANTHROPIC_BASE_URL=http://127.0.0.1:4318/proxy/anthropic/v1
```

Proxy mode creates **provisional** episodes so you can validate that Juvera sees traffic. Upgrade to SDK or attach mode for attribution and experiments.

### SDK mode through the relay

```python
j.init(
    endpoint="http://127.0.0.1:4318",
    domain="support",
)
```

### Validate your setup

```bash
juvera doctor --scan-ports
juvera validate
```

`juvera validate` checks whether your latest traffic includes the fields Juvera needs for attribution readiness and spend attribution: `agent_id`, `workflow_type`, `work_item_id`, provider/model detection, token capture, pricing resolution, and cost computation.

`juvera patch` reads the current repo, detects common frameworks, and prints the recommended `wrap_*()` or `instrument_*()` upgrade snippet.

---

## Claude Code Plugin

The SDK ships with a [Claude Code plugin](claude-plugin/) that auto-detects your AI framework (OpenAI, Anthropic, LangChain, CrewAI, LlamaIndex) and instruments it with Juvera — no manual setup needed.

### Install

**Marketplace (recommended):**

```bash
/plugin marketplace add Juvera-AI/juvera-python
/plugin install juvera@juvera-plugins
```

**Git URL:**

```bash
claude plugin add https://github.com/Juvera-AI/juvera-python/tree/main/claude-plugin
```

**Local (from a clone):**

```bash
git clone https://github.com/Juvera-AI/juvera-python.git
claude plugin add ./juvera-python/claude-plugin
```

### Commands

| Command | What it does |
|---|---|
| `/juvera-instrument` | Detect framework and add instrumentation (progressive Tier 1→2→3) |
| `/juvera-instrument validate` | Check instrumentation correctness |
| `/juvera-instrument roi` | Estimate ROI using workflow baselines |

### What it does

1. **Detects** your AI framework from imports
2. **Adds** `juvera_sdk` init, spans, and flush — progressively (Tier 1 → 2 → 3)
3. **Validates** your instrumentation and flags missing pieces
4. **Estimates** ROI against human-baseline benchmarks

The plugin also includes an MCP server with `juvera_validate` and `juvera_roi` tools for programmatic access.

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

## ROI estimation

Most companies can't answer "what's this agent worth?" The SDK ships with **workflow baselines** — industry-standard benchmarks for common agent tasks:

| Workflow Type | Human Cost | Human Time |
|---|---|---|
| `ticket_deflection` | $22 | 15 min |
| `lead_qualification` | $35 | 25 min |
| `document_review` | $75 | 45 min |
| `data_extraction` | $18 | 12 min |
| `code_review` | $95 | 30 min |
| `compliance_check` | $120 | 60 min |
| `content_generation` | $50 | 30 min |

Set `workflow_type` on your span, then call `estimate_roi()`:

```python
with j.agent_span(agent_id="a1", work_item_id="wi_001",
                   workflow_type="ticket_deflection") as span:
    # ... agent logic ...
    roi = j.estimate_roi(agent_cost_usd=2.50)
    # roi = {'estimated_savings_usd': 19.50, 'baseline_cost_usd': 22.0, ...}
```

Override defaults with your own baselines:

```python
j.init(
    api_key="jvr_key", org_id="org_id",
    workflow_baselines={"internal_review": {"human_cost_usd": 60.0, "human_time_minutes": 40}},
)
```

---

## Custom events

Record guardrail checks, cache hits, retrievals, and other custom node types:

```python
with j.agent_span(agent_id="a1", work_item_id="wi_001"):
    j.record_event("guardrail_check", status="success", properties={"rule": "pii_filter"})
    j.record_event("cache_hit", properties={"cache_key": "user_123"})
```

---

## Multi-provider normalization

Teams using Phoenix, Langfuse, or Braintrust get automatic attribute normalization. Third-party attributes are mapped to Juvera conventions — no code changes needed:

| Source Attribute | Normalized To |
|---|---|
| `input.value` (Phoenix) | `gen_ai.prompt` |
| `output.value` (Phoenix) | `gen_ai.completion` |
| `langfuse.input` / `langfuse.output` | `gen_ai.prompt` / `gen_ai.completion` |
| `braintrust.input` / `braintrust.output` | `gen_ai.prompt` / `gen_ai.completion` |
| `llm.token_count.prompt` / `llm.token_count.completion` | `gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens` |

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
| `j.init(api_key, org_id, ..., workflow_baselines)` | Configure once at startup |
| `j.agent_span(agent_id, work_item_id, workflow_type, ...)` | Context manager for one unit of work. Yields `AgentSpan`. |
| `span.set_model(model, provider)` | Record which LLM was used |
| `span.set_tokens(input, output)` | Record token consumption |
| `span.set_prompt(text)` | Record the prompt sent to the model |
| `span.set_completion(text)` | Record the model's completion/response |
| `span.add_context_source(name, doc_type, token_count)` | Record a RAG context source |
| `span.add_tool_call(name, status, duration_ms, error)` | Record a tool/function call with optional timing and error |
| `span.set_error(exception)` | Mark span as errored |
| `j.record_event(event_type, status, properties)` | Record a custom event (guardrail, cache hit, etc.) |
| `j.estimate_roi(workflow_type, agent_cost_usd)` | Estimate ROI using workflow baselines |
| `j.record_impact_signal(impact_type, value, ...)` | Emit a business outcome event |
| `j.record_handoff(reason, reviewer_role)` | Record a human-in-the-loop handoff |
| `j.set_work_item(work_item_id, workflow_type)` | Set work item context for downstream spans |
| `j.clear_work_item()` | Clear work item context |
| `j.flush()` | Force-export buffered spans. In debug mode, prints run summary. |
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
| `workflow_baselines` | `None` | Custom ROI baselines `{"type": {"human_cost_usd": N, "human_time_minutes": N}}` |

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
