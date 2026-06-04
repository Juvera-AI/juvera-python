---
workflow_type: compliance_check
human_cost_usd: 120.0
human_cost_usd_range: [50.0, 180.0]
human_time_minutes: 60
human_time_minutes_range: [45, 90]
confidence: medium
sources:
  - title: "AgentiveAIQ — How to Calculate AI Automation Costs for Compliance"
    url: https://agentiveaiq.com/blog/how-to-calculate-ai-automation-costs-for-compliance
    year: 2026
  - title: "SQ Magazine — AI Compliance Cost Statistics 2026"
    url: https://sqmagazine.co.uk/ai-compliance-cost-statistics/
    year: 2026
  - title: "Digiqt — AI Agents in Regulatory Compliance"
    url: https://digiqt.com/blog/ai-agents-in-regulatory-compliance/
    year: 2026
  - title: "Lyzr — AI Agents for Compliance Checks"
    url: https://www.lyzr.ai/blog/ai-agents-for-compliance-checks/
    year: 2025
  - title: "BLS Occupational Employment Statistics May 2025 — 13-1041 Compliance Officers"
    url: https://www.bls.gov/oes/tables.htm
    year: 2025
method: |
  Midpoint = senior compliance officer fully-loaded rate per BLS 2025 (13-1041 Compliance
  Officers median ~$36/hr; fully-loaded $55-75/hr; senior compliance counsel $100-150/hr)
  × 60 min = $120. Range spans compliance analyst handling routine AML alerts (low, $50
  ~ analyst at $65/hr × 50 min per AgentiveAIQ 2026) and senior compliance counsel
  reviewing regulatory filings (high, $180 ~ $150/hr × 75 min). The 60-min midpoint
  reflects standard regulated-industry compliance review.
last_reviewed: 2026-05-27
---

# Compliance check

Regulated-industry compliance review: a compliance officer, analyst, or counsel reviews a
transaction, document, decision, or system output against regulatory requirements
(AML/KYC, HIPAA, SOX, GDPR, fair lending, financial reporting). The baseline measures the
cost of a human compliance check at a regulated organization.

## What's in scope

- AML/KYC alert review and disposition
- HIPAA compliance review of patient data flows
- SOX control walkthroughs and evidence review
- GDPR data-subject request handling and review
- Vendor risk-assessment reviews

## What's not in scope

- Strategic compliance program design (different work, different unit cost)
- External audit work (separate engagement; not a per-workflow cost)
- Compliance training development

## Methodology

The $120 midpoint comes from:

- **Senior compliance officer fully-loaded rate**: BLS 2025 13-1041 median $36/hr →
  fully-loaded $55-75/hr (analyst tier); senior compliance counsel $100-150/hr. At a
  senior officer / counsel blend of ~$120/hr × 60 min = $120.

- **Industry anchor (AgentiveAIQ 2026)**: mid-size FI with 800 AML alerts/mo at 75 min
  average handle time at $65/hr fully-loaded analyst = $81/alert. Our $120/60min sits
  higher because it covers more senior tiers and complex non-AML reviews (HIPAA, SOX).

## Override pattern

Small or pre-IPO companies with junior compliance staff should override downward.
Banks and large healthcare orgs with senior compliance counsel doing review should
override upward.

```python
j.init(
    workflow_baselines={
        "compliance_check": {"human_cost_usd": 80.0, "human_time_minutes": 60},
    },
)
```

## Last reviewed

2026-05-27. Next review: 2027-05-27.
