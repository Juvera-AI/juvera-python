---
workflow_type: ticket_deflection
human_cost_usd: 22.0
human_cost_usd_range: [15.0, 32.0]
human_time_minutes: 15
human_time_minutes_range: [10, 25]
confidence: medium
sources:
  - title: "Zendesk CX Trends 2026"
    url: https://cxtrends.zendesk.com/
    year: 2026
  - title: "Forrester TEI — Salesforce Agentforce for Customer Service"
    url: https://tei.forrester.com/go/Salesforce/Agentforce/?lang=en-us
    year: 2025
  - title: "Forrester TEI — Zendesk Advanced AI"
    url: https://tei.forrester.com/go/zendesk/advancedaisupport/
    year: 2025
  - title: "BLS Occupational Employment Statistics May 2025 — 43-4051 Customer Service Representatives"
    url: https://www.bls.gov/oes/tables.htm
    year: 2025
method: |
  Midpoint = fully-loaded labor rate per BLS 2025 (43-4051 Customer Service Representatives,
  ~$35/hr fully-loaded) × 15 min average handle time + customer-service downstream overhead
  (escalation, supervision, infrastructure, QA) per Zendesk CX Trends 2026 cost-per-resolution
  baseline of $7.40 human resolution. Range reflects 80th-percentile spread observed across
  Forrester TEI vendor studies (Salesforce Agentforce, Zendesk Advanced AI, boost.ai) in SaaS,
  enterprise, and BPO verticals.
last_reviewed: 2026-05-27
---

# Ticket deflection

Customer-service ticket resolution: an inbound user question lands in your help desk
(Zendesk, Salesforce Service Cloud, Intercom, internal queue) and an agent either resolves
it directly or escalates. The baseline measures the cost of a human resolution at the median
mid-market organization.

## What's in scope

- Tier-1 support tickets resolved without engineering or specialist handoff
- Standard inquiry types: refund status, account access, password resets, product how-to,
  basic troubleshooting
- Both chat and email channels (voice has different unit economics; see Range below)

## What's not in scope

- Tier-2/3 escalations requiring engineering or specialist time
- Voice-only call centers (cost-per-resolution is materially higher; the $22 baseline does
  not apply)
- Compliance-laden support (HIPAA, financial services) — use `compliance_check` workflow
  instead

## Methodology

The $22 midpoint comes from blending two anchor points:

1. **Direct labor cost**: BLS May 2025 occupational employment statistics for SOC code
   43-4051 (Customer Service Representatives) puts median hourly wage at ~$20-25. Adding
   typical fully-loaded overhead (benefits, employer taxes, office, equipment, training,
   supervision allocation) brings this to ~$30-40/hr. At a 15-minute average handle time,
   raw labor is $7.50-10.

2. **Industry per-ticket benchmark**: Zendesk CX Trends 2026 reports $7.40 per human
   resolution as an industry baseline; this already includes some downstream overhead.
   Adding tooling cost (help desk platform license + integrations prorated per ticket)
   and supervisor allocation closes the gap to $22.

The $15 lower bound represents BPO/offshore operations and high-automation tier-1 support;
the $32 upper bound represents premium SaaS support with senior agents and shorter SLAs.

## Override pattern

If your organization runs offshore (real cost ~$10-15/ticket) or premium support (real cost
$35-50/ticket), override the baseline at SDK initialization:

```python
import juvera_sdk as j

j.init(
    api_key="...",
    org_id="...",
    workflow_baselines={
        "ticket_deflection": {
            "human_cost_usd": 12.0,
            "human_time_minutes": 8,
        }
    },
)
```

`estimate_roi()` calls will use your numbers instead of the default.

## Last reviewed

2026-05-27. Next review: 2027-05-27 (annual review cadence).
