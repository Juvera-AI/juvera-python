# Changelog

All notable changes to `juvera-sdk` are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/)

---

## [0.2.0] — 2026-05-10

### Added
- `juvera demo` — synthetic ticket-deflection agent run + styled ROI card. Pure local; no API key, no account. Flags: `--no-save`, `--workflow`, `--seed`, `--live` (deferred warning).
- `juvera report` — self-contained HTML ROI report (Jinja2, autoescape on) generated from local NDJSON captures; auto-opens in browser. `--format md` available; `--since 24h/7d/30d/all` with hour-precision; `--source demo|capture|all`.
- `juvera config get/set/unset` — read/write `~/.juvera/config.json`. `install_id` is system-managed and rejected by `set`.
- `juvera listen` — keyless mode is now the default (writes to `~/.juvera/captures/<date>/` only). Cloud upload requires `JUVERA_API_KEY` (or `JUVERA_SETUP_TOKEN` / `--setup-token` for onboarding). New `--local` flag forces local-only even if either credential is set; setup-token bootstrap is skipped when `--local` is set so the relay doesn't depend on the API base URL being reachable. Mandatory startup banner shows the active mode.
- `from juvera_sdk import estimate_roi` — pure, callable without `j.init()`. Falls back to default `WORKFLOW_BASELINES`.
- Local NDJSON storage layer at `~/.juvera/captures/<date>/<source>-<ulid>.ndjson`.
- Opt-in anonymous telemetry: consent prompt deferred until **after** the primary command output. Strict per-command flag allowlist; flag values are never transmitted. Sender no-ops when no endpoint is configured.
- Local metrics counters at `~/.juvera/metrics.json` (always-on, never sent unless opted in).
- Pricing catalog vendored inside the SDK package (`juvera_sdk/data/model_pricing.json`); `compute_token_cost_usd()` now works from a wheel install.

### Changed
- `estimate_roi()` rounds to 6 decimal places (was 2) so sub-cent costs from cheap models are preserved internally. User-visible `$` and `%` formatting in the demo card and HTML report uses 2 decimal places.
- `juvera listen` upload path is best-effort: network failures log a warning and the relay continues capturing locally rather than crashing. New `_try_upload_capture()` helper.

### Packaging
- `MANIFEST.in` now includes `juvera_sdk/templates/*.j2` and `juvera_sdk/data/*.json`.
- `pyproject.toml [tool.setuptools.package-data]` includes the same.
- New runtime dependency: `jinja2>=3.0,<4.0`.
- New dev dependency: `build>=1.0` (for `test_packaging.py` and `test_wheel_install_e2e.py`).

## [0.1.6] — 2026-03-24

### Added

- **Prompt/Completion Capture**: `span.set_prompt(text)` and `span.set_completion(text)` to record what the agent said
- **Context Sources**: `span.add_context_source(name, doc_type, token_count)` for RAG pipeline visibility
- **Enhanced Tool Calls**: `span.add_tool_call()` now accepts `duration_ms` and `error` parameters
- **Custom Events**: `j.record_event(event_type, status, properties)` for guardrails, cache hits, retrievals
- **ROI Estimator**: `j.estimate_roi(workflow_type, agent_cost_usd)` with industry-standard workflow baselines
- **Workflow Baselines**: 7 built-in baselines (ticket_deflection, lead_qualification, document_review, data_extraction, code_review, compliance_check, content_generation)
- **Custom Baselines**: `j.init(workflow_baselines={...})` to override defaults
- **Attribute Normalizer**: Automatic mapping of Phoenix, Langfuse, and Braintrust attributes to Juvera conventions
- **Debug Run Summary**: Aggregated stats printed on `j.flush()` in debug/local mode

### Changed

- `agent_span()` now propagates `workflow_type` into ContextVar for downstream use by `estimate_roi()`

## [0.1.5] — 2026-03-22

### Added

- `JuveraSpanProcessor` — standard OTel `SpanProcessor` for attach mode. Works with any `TracerProvider` (Phoenix, Langfuse, raw OTel). Use `provider.add_span_processor(JuveraSpanProcessor(...))` alongside your existing telemetry.
- `set_work_item(work_item_id, workflow_type=None)` / `clear_work_item()` — context helpers for middleware and request handlers where `work_item_id` is known at the top of the call stack but `agent_span()` is called deeper.
- PII detection (warn-only) — scans span attributes for email, phone, SSN, credit card, and API key patterns in debug/local mode. Prints warnings to stderr. Never modifies span data.

### Changed

- `init()` refactored internally to use `JuveraSpanProcessor`. Public API unchanged — all v0.1.4 code works without modification.
- `agent_span()` now reads `work_item_id` and `workflow_type` from ContextVar as fallback (priority: explicit arg > ContextVar > auto-UUID).

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

