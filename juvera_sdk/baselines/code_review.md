---
workflow_type: code_review
human_cost_usd: 50.0
human_cost_usd_range: [20.0, 95.0]
human_time_minutes: 30
human_time_minutes_range: [20, 45]
confidence: medium
sources:
  - title: "GitAutoReview — Reduce Code Review Time by 67% with AI"
    url: https://gitautoreview.com/blog/how-to-reduce-code-review-time
    year: 2025
  - title: "Graphite — ROI of AI-Assisted Code Review"
    url: https://graphite.com/guides/roi-of-ai-assisted-code-review
    year: 2025
  - title: "SitePoint — AI Coding Tools ROI Calculator 2026"
    url: https://www.sitepoint.com/ai-coding-tools-cost-analysis-roi-calculator-2026/
    year: 2026
  - title: "Vitalii Petrenko — The Hidden Cost of Slow Code Reviews (8M PRs)"
    url: https://medium.com/@vitalii4reva/the-hidden-cost-of-slow-code-reviews-data-from-8-million-prs-9926849f1428
    year: 2025
  - title: "BLS Occupational Employment Statistics May 2025 — 15-1252 Software Developers"
    url: https://www.bls.gov/oes/tables.htm
    year: 2025
method: |
  Midpoint = fully-loaded median senior software developer rate per BLS 2025 (15-1252:
  median annual wage $133K → median hourly $64; fully-loaded with overhead $80-120/hr;
  median fully-loaded ~$100/hr) × 30 min review time = $50. Range spans junior dev
  ($20-30/hr fully-loaded × 30 min = $10-15) and senior staff engineer at tech-company-tier
  total comp ($190/hr × 30 min = $95). Customers operating in markets where dev rates
  differ — particularly FAANG-tier teams where fully-loaded TC reaches $200/hr+ — should
  override via `j.init(workflow_baselines={...})`. The 30-min midpoint reflects industry
  data of 20-30 min review time per PR (GitAutoReview, Graphite).
last_reviewed: 2026-05-27
---

# Code review

Pull-request review by a peer engineer: reading code changes, running mental
type-checking, spotting bugs or anti-patterns, leaving comments, and approving or
requesting changes. The baseline measures the cost of a single reviewer's time per PR
at a median engineering organization.

## Important: baseline change in v0.2.3

In SDK versions ≤ 0.2.2, this baseline shipped at **$95/30 min** — implying a $190/hr
fully-loaded rate. That rate is FAANG-tier senior engineer territory; it is not the
industry median. Skeptical readers running the math against BLS 2025 ($64/hr median)
would correctly call the old number unsupportable.

v0.2.3 lowers the midpoint to **$50** (median senior dev × 30 min) and adds an explicit
range [$20, $95] covering junior through FAANG-tier. **FAANG-tier teams should override
upward.**

## What's in scope

- Standard PR review by one peer reviewer
- Comment-and-revision cycles within the same PR
- Mental complexity-checking, bug-spotting, suggesting alternative approaches

## What's not in scope

- Architecture reviews / design docs (different unit economics)
- Security audits (specialist time; use a custom workflow)
- Compliance code review (use `compliance_check` workflow)
- AI-mediated reviews (this baseline is the *human* cost being saved)

## Methodology

The $50 midpoint reflects:

- **BLS 2025 median software developer**: SOC 15-1252 median annual $133K → ~$64/hr.
  Fully-loaded (benefits, overhead, equipment, supervision) typically $80-120/hr;
  median around $100/hr.

- **30-min review time**: industry data (GitAutoReview, Graphite) consistently puts
  human PR review at 20-30 min; the 30-min midpoint is consistent.

- **$100/hr × 30 min = $50**.

The $20 lower bound reflects junior engineers at smaller companies; the $95 upper bound
reflects senior staff or principal engineers at tech-company-tier total compensation.

## Override pattern — FAANG-tier teams

If your engineering team is at a tech-company-tier compensation level (fully-loaded
$150-200/hr for senior engineers), the default $50 understates your reality. Override:

```python
j.init(
    workflow_baselines={
        "code_review": {"human_cost_usd": 95.0, "human_time_minutes": 30},
    },
)
```

## Override pattern — offshore / open source

If your code reviews are predominantly handled by offshore teams or open-source
maintainers at substantially lower fully-loaded rates, override downward:

```python
j.init(
    workflow_baselines={
        "code_review": {"human_cost_usd": 15.0, "human_time_minutes": 20},
    },
)
```

## Last reviewed

2026-05-27. Next review: 2027-05-27.
