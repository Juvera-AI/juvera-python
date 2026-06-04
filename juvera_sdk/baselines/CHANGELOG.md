# Baseline methodology changelog

Reverse-chronological log of changes to the 7 workflow baselines published in
`juvera_sdk/baselines/` and consumed by `juvera_sdk.roi.WORKFLOW_BASELINES`. Every change to
any baseline number, range, confidence band, or source list gets a dated entry.

For methodology rationale per baseline, see the individual `<workflow>.md` files or
the published page at <https://juvera.ai/baselines>.

---

## 2026-05-27 — unreleased (lands in v0.2.3 once Phase 2 methodology page is live)

> The SDK code changes below were merged to `main` as part of the Phase 1 PR for #161.
> The PyPI release (`v0.2.3`) is intentionally deferred until the apps/www `/baselines`
> page is deployed, so `source_url` values resolve. Phase 2 plan handles the version
> bump + tag + release.

First published methodology page. All 7 baselines transitioned from undocumented
hardcoded values to fully-cited entries with:
- midpoint number (canonical, used by `estimate_roi()`)
- range [low, high]
- confidence band (low / medium / high)
- source list (≥1 per baseline; BLS 2025 + industry-report citations)
- `last_reviewed` date

### Value changes from v0.2.2

- **`code_review`**: midpoint $95 → **$50** (30 min unchanged). Range added: [20, 95].
  Reason: $95 implied a $190/hr fully-loaded rate, which is FAANG-tier senior engineer
  compensation, not the BLS 2025 median ($64/hr → ~$100/hr fully-loaded). A skeptical
  reader running the math against BLS data would correctly flag $95 as unsupportable
  for the median engineering organization.

  **Behavioral impact:** `j.estimate_roi("code_review", ...)` now returns smaller
  `estimated_savings_usd` for any given `agent_cost_usd`. The savings are not actually
  smaller — the previous baseline overstated what was being saved.

  **Migration for FAANG-tier teams:** if your fully-loaded senior engineer rate is
  $150-200/hr, override the baseline at SDK initialization to preserve the previous
  behavior:

  ```python
  j.init(
      api_key="...",
      org_id="...",
      workflow_baselines={
          "code_review": {"human_cost_usd": 95.0, "human_time_minutes": 30},
      },
  )
  ```

- All other 6 baselines retain their midpoint values. They gain range fields but
  their `human_cost_usd` and `human_time_minutes` are unchanged.

### Documentation changes

- New: `juvera_sdk/baselines/<workflow>.md` (×7) with frontmatter + methodology narrative.
- New: `tests/test_baselines_sync.py` and `tests/test_estimate_roi_provenance.py`
  enforce drift-free alignment.
- New: `juvera demo`, `juvera report`, and `processor.py` ROI banner now surface
  `confidence` + methodology URL.
- `estimate_roi()` return dict gains two keys: `confidence`, `source_url`.
- `README.md:325` retires "industry-standard benchmarks" wording.

### Known follow-up

URLs of the form `https://juvera.ai/baselines#<workflow>` are baked into the
SDK code (`roi.py` dict, `estimate_roi()` return, CLI output, README link, this
CHANGELOG) but will not resolve to actual anchors until the apps/www methodology
page deploys in Phase 2 of #161. **Because the v0.2.3 PyPI release is gated on
Phase 2 being live**, no installed-from-PyPI user will encounter these 404s in
the wild — the URLs go live the same day v0.2.3 publishes.

**Same version, two behaviors (source installs only):** between this PR
merging to `main` and the v0.2.3 PyPI publish, `pyproject.toml` will read
`version = "0.2.2"` while the `code_review` baseline behaviorally returns
`$50` (not the `$95` that ships in PyPI's `juvera-sdk==0.2.2`). Anyone who
`pip install`s from a git checkout of `main` during that window gets
different behavior under an identical version string than they would from
`pip install juvera-sdk==0.2.2`. PyPI users are unaffected; source-install
users should be aware.

**Uniform `confidence: medium` across all 7 baselines (v0.2.3):** the
initial methodology launch ships every baseline at `medium` confidence.
This is honest about where the data is today — no baseline has the
`high` calibration that would require a wider, more independent source
panel (e.g. multiple peer-reviewed primary sources cross-checking the
same midpoint), and none has the gap that would warrant `low`. A future
revision (likely v0.3.x) may differentiate — `ticket_deflection` (Forrester
TEI cluster + Zendesk CX Trends + BLS, tight $15-$32 range) is a stronger
candidate for `high` than `document_review` (single Wolters Kluwer
datapoint + 4.6× range spread), but the methodology page launch is too
new to make those distinctions reliably.
