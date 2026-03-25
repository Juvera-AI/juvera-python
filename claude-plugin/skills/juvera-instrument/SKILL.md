---
name: juvera-instrument
description: Auto-instrument AI agent code with Juvera SDK for ROI tracking. Use when code imports openai, anthropic, langchain, crewai, llama_index, or makes LLM API calls. Also activates on "add juvera", "instrument this", "track ROI", or /juvera.
metadata:
  mcp-server: juvera
---

# Juvera Instrumentation Skill

Add [Juvera SDK](https://pypi.org/project/juvera-sdk/) instrumentation to AI agent code for ROI tracking, trace capture, and business impact measurement.

## When This Skill Activates

**Semi-automatic detection** — activate when you see ANY of these in code you're writing or reading:

| Pattern | Framework |
|---------|-----------|
| `from openai import OpenAI` or `import openai` | OpenAI SDK |
| `import anthropic` or `from anthropic` | Anthropic SDK |
| `from langchain` | LangChain |
| `from crewai` | CrewAI |
| `from llama_index` | LlamaIndex |
| `requests.post(...)` / `httpx.post(...)` targeting LLM APIs | Raw HTTP |
| `@app.post` / `@app.route` with LLM calls inside | FastAPI/Flask |

When detected, say: "I notice you're using [framework] — want me to add Juvera tracking so you can measure your agent's ROI?"

**Explicit activation** — user says "add juvera", "instrument this", "track ROI", or uses `/juvera`.

## The Flow

### Step 1: Configuration Bootstrap

Before adding any instrumentation, handle init() setup:

1. Check if code already has `j.init()` or `juvera_sdk.init()` — if so, skip to Step 2
2. Ask: "Do you have a Juvera API key, or should I set up local debug mode?"
3. **Local debug mode** (default for new users):
   ```python
   import os
   import juvera_sdk as j

   j.init(
       api_key=os.environ.get("JUVERA_API_KEY", "jvr_local"),
       org_id=os.environ.get("JUVERA_ORG_ID", "org_local"),
       endpoint="local",
       debug=True,
   )
   ```
4. **With credentials**: guide to env vars approach (never hardcode keys)

### Step 2: Tier 1 — Minimal Instrumentation

Add the basics. Always include `workflow_type` (infer from context):

| Code Context | Suggested workflow_type |
|---|---|
| Support bot, ticket handling, customer service | `ticket_deflection` |
| Sales bot, lead scoring, SDR automation | `lead_qualification` |
| Document analysis, legal review | `document_review` |
| Data parsing, extraction, ETL | `data_extraction` |
| Code assistant, PR review | `code_review` |
| Compliance checking, audit | `compliance_check` |
| Blog writing, email drafting | `content_generation` |

**What to add:**
- `import juvera_sdk as j` at top
- `j.init(...)` (from Step 1)
- Wrap the main LLM call in `with j.agent_span(agent_id="...", workflow_type="...") as span:`
- Inside the span: `span.set_model(model_name, provider="provider")`
- After the LLM response: `span.set_tokens(input=..., output=...)` from usage data
- At end of script/app lifecycle: `j.flush()` and `j.shutdown()`
- For FastAPI/Flask: add `j.set_work_item(request_id)` at request start, `j.clear_work_item()` at end

**Framework-specific token extraction:**

```python
# OpenAI
span.set_tokens(input=response.usage.prompt_tokens, output=response.usage.completion_tokens)

# Anthropic
span.set_tokens(input=response.usage.input_tokens, output=response.usage.output_tokens)

# LangChain (with callback)
# Use get_openai_callback() or token_counter callback

# CrewAI
# Extract from crew.usage_metrics after kickoff

# LlamaIndex
# Extract from response.metadata or token_counter callback
```

After inserting Tier 1, say:
> "Basic Juvera tracking is set up. I can also add prompt/completion capture and tool call tracking — want me to?"

### Step 3: Tier 2 — Standard (only if user says yes)

Add inside the agent_span:
- `span.set_prompt(user_message)` — capture the input
- `span.set_completion(response_text)` — capture the output
- `span.add_tool_call("tool_name", status="success", duration_ms=N)` — for any tool/function calls

After inserting Tier 2, say:
> "Now tracking prompts, completions, and tool calls. I can also add ROI estimation, custom events, error handling, and business impact signals — want the full setup?"

### Step 4: Tier 3 — Full (only if user says yes)

Add:
- `span.add_context_source("source_name", doc_type="pdf", token_count=N)` for RAG/retrieval
- `j.record_event("event_name", status="success", properties={...})` for guardrails, cache hits
- `roi = j.estimate_roi(agent_cost_usd=N)` for inline ROI
- Wrap span body in try/except with `span.set_error(e)` and `j.record_handoff(reason, reviewer_role)`
- `j.record_impact_signal(impact_type, value, impact_category, source_system)` for business outcomes

### Step 5: Validate

After instrumentation is complete, use the `juvera_validate` MCP tool to check the file:
- Fix any errors (missing init, flush, shutdown)
- Note any warnings for the user

## Important Rules

1. **Never auto-instrument without consent** — always ask first
2. **Never hardcode API keys** — use environment variables
3. **Always include workflow_type** — it's required for ROI to work
4. **Progressive, not pushy** — offer each tier once, don't nag
5. **Adapt to existing code** — don't restructure the user's code, wrap around it
6. **If MCP tools are unavailable**, the skill still works — use the patterns above directly
7. **Multiple frameworks** — if code uses multiple LLM frameworks (e.g., OpenAI + LangChain), ask which is the primary agent. Create separate `agent_span()` blocks for each distinct LLM call site.
8. **Async code** — `agent_span()` is a sync context manager. It works inside async functions but wrap only the synchronous LLM call section. For async FastAPI routes, place `agent_span()` around the `await` call to the LLM.

## Workflow Baselines Reference

| Workflow Type | Human Cost | Human Time |
|---|---|---|
| `ticket_deflection` | $22 | 15 min |
| `lead_qualification` | $35 | 25 min |
| `document_review` | $75 | 45 min |
| `data_extraction` | $18 | 12 min |
| `code_review` | $95 | 30 min |
| `compliance_check` | $120 | 60 min |
| `content_generation` | $50 | 30 min |
