# Changelog

All notable changes to `juvera-sdk` are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/)

---

## [0.1.4] — 2026-03-20

### Docs — contract clarification

- `work_item_id` is preserved in `impact.properties.work_item_id` in the emitted impact signal payload. This is the correct and stable location for `0.1.x`.
- `work_item_id` is **not** part of the `agent` block. The gateway schema enforces `additionalProperties: false` on that block; adding `workItemId` there would cause 422 errors.
- A future schema version may promote `work_item_id` to a first-class context field (e.g. `context.workItemId`), with a backward-compatible migration path. That is not part of the `0.1.x` contract.
- README expanded with an explicit "Where `work_item_id` appears" table and JSON example.

No SDK code changes in this release. All 23 tests pass.

## [0.1.3] — 2026-03-20

### Fixed

- Handoff spans now inherit `juvera.agent_id` from the enclosing `agent_span` context (was `None` in v0.1.2)

### Added

- `examples/support_roi.py` — runnable OpenAI + Juvera integration example with local-mode fallback

### Docs

- README: added "Two happy paths" section (local debug + real model call with OpenAI)
- README: expanded common gotchas with `work_item_id` location clarification and flush reminder

## [0.1.2] — 2026-03-20

### Changed

- Version bump to 0.1.2 (0.1.1 PyPI upload was incomplete)

## [0.1.1] — 2026-03-20

### Fixed

- `work_item_id` now preserved in `impact.properties` so the server-side attribution join works correctly (was silently dropped in v0.1.0)
- `debug=True` in `init()` now suppresses HTTP in `record_impact_signal()` — same behaviour as `endpoint="local"` (was firing real HTTP and raising connection errors)
- Added `__version__` attribute — `juvera_sdk.__version__` no longer raises `AttributeError`
- `record_handoff()` now emits `UserWarning` when called outside an active `agent_span` with no `work_item_id`, preventing silent trace disconnection
- README rewritten with 30-second quickstart, core concepts, what gets emitted, common gotchas, and API reference
- Added `examples/local_debug.py` — canonical local validation script

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
