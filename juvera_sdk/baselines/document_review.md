---
workflow_type: document_review
human_cost_usd: 75.0
human_cost_usd_range: [30.0, 140.0]
human_time_minutes: 45
human_time_minutes_range: [30, 60]
confidence: medium
sources:
  - title: "Wolters Kluwer — Legal AI Adoption: Time Savings, Contract Review, Revenue Growth"
    url: https://www.wolterskluwer.com/en/expert-insights/legal-ai-adoption-time-savings-revenue-growth
    year: 2025
  - title: "Thomson Reuters CoCounsel"
    url: https://legal.thomsonreuters.com/en/products/cocounsel-legal
    year: 2025
  - title: "American Bar Association — How AI Enhances Legal Document Review (2025)"
    url: https://www.americanbar.org/groups/law_practice/resources/law-technology-today/2025/how-ai-enhances-legal-document-review/
    year: 2025
  - title: "MyCase — AI for Legal Document Review"
    url: https://www.mycase.com/blog/ai/ai-for-legal-document-review/
    year: 2025
  - title: "BLS Occupational Employment Statistics May 2025 — 23-2011 Paralegals, 23-1011 Lawyers"
    url: https://www.bls.gov/oes/tables.htm
    year: 2025
method: |
  Midpoint = fully-loaded labor rate per BLS 2025 (23-2011 Paralegals median $33.51/hr →
  fully-loaded $50-65/hr; 23-1011 Lawyer median ~$66/hr → fully-loaded $95-130/hr;
  blended at junior-associate ~$100/hr) × 45 min standard contract review = $75. Range
  spans paralegal-tier routine review (low) and junior-associate complex contract analysis
  (high). Wolters Kluwer references NDA review reducing 2 hr → 30 min with AI; our 45-min
  human midpoint is consistent with mixed-complexity workloads.
last_reviewed: 2026-05-27
---

# Document review

Legal or compliance document review: a paralegal or junior associate reads a contract,
NDA, lease, vendor agreement, or similar legal document and flags issues, checks against
playbook clauses, or summarizes for an attorney's sign-off.

## What's in scope

- NDA and routine commercial contract review
- Vendor agreement comparison against template/playbook
- Compliance read-through (privacy, IP, indemnification clauses)
- Discovery document categorization and relevance flagging

## What's not in scope

- Strategic contract drafting (writing, not reviewing)
- Litigation document review at e-discovery scale (separate workflow, different unit
  economics)
- Regulatory filings (use `compliance_check` workflow instead)

## Methodology

The $75 midpoint comes from:

- **Junior associate fully-loaded rate**: $100/hr × 45 min = $75. Matches the Wolters
  Kluwer datapoint of 2 hr → 30 min NDA review, where 2 hr × $100/hr = $200 maps to
  complex contracts; our 45-min midpoint maps to mid-complexity routine review.

- **Paralegal-tier (low end)**: BLS 2025 23-2011 paralegal fully-loaded $50-65/hr × 30 min
  routine review = ~$30.

- **Senior associate (high end)**: $130/hr × 60 min complex review = ~$130-140.

## Override pattern

Boutique law firms or in-house teams with senior counsel doing review should override
upward. AmLaw 100 firms with structured paralegal review should override downward.

```python
j.init(
    workflow_baselines={
        "document_review": {"human_cost_usd": 50.0, "human_time_minutes": 30},
    },
)
```

## Last reviewed

2026-05-27. Next review: 2027-05-27.
