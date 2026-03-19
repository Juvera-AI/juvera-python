# Changelog

All notable changes to `juvera-sdk` are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/)

---

## [0.1.0] — 2026-03-19

### Added

- `juvera_sdk.init()` — configure the SDK with API key, org, endpoint, domain
- `juvera_sdk.agent_span()` — context manager wrapping one unit of agent work
  - `AgentSpan.set_model(model, provider)` — record the LLM used
  - `AgentSpan.set_tokens(input, output)` — record token consumption
  - `AgentSpan.add_tool_call(name, status)` — record tool/function calls
  - `AgentSpan.set_error(exception)` — mark span as errored
- `juvera_sdk.record_impact_signal()` — emit a business outcome event to `/v1/impact-signals`
- `juvera_sdk.record_handoff()` — record a human-in-the-loop handoff as an OTel child span
- `juvera_sdk.flush()` / `juvera_sdk.shutdown()` — lifecycle management
- `JuveraSpanExporter` — converts OTel `ReadableSpan` objects to `TraceIngestEnvelope` JSON
- `MockExporter` — captures spans in memory for tests (no network calls)
- `DebugExporter` — prints spans to stdout when `endpoint="local"`
- `ImpactSignal` Pydantic model matching the Juvera ingest gateway JSON schema
- Model cost table (`MODEL_COSTS_USD_PER_TOKEN`) for Claude, GPT-4o, Gemini
- `compute_token_cost_usd(model, input_tokens, output_tokens)` utility
- 18 unit tests
- 3 example scripts (manual instrumentation, OpenAI, LangChain)
- CI with OSS boundary enforcement
