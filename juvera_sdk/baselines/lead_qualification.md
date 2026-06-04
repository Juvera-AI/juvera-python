---
workflow_type: lead_qualification
human_cost_usd: 35.0
human_cost_usd_range: [20.0, 60.0]
human_time_minutes: 25
human_time_minutes_range: [10, 30]
confidence: medium
sources:
  - title: "Gartner — Sales Development Metrics: Assessing Low Conversion Rates"
    url: https://www.gartner.com/smarterwithgartner/sales-development-metrics-assessing-low-conversion-rates
    year: 2024
  - title: "Gradient.works — 2025 B2B Sales Performance Benchmarks"
    url: https://www.gradient.works/blog/2025-b2b-sales-performance-benchmarks
    year: 2025
  - title: "BLS Occupational Employment Statistics May 2025 — 41-3091 / 41-3099 Sales Representatives"
    url: https://www.bls.gov/oes/tables.htm
    year: 2025
  - title: "Landbase — The Real Cost of Manual Lead Qualification: A 2026 Analysis (vendor; secondary illustration)"
    url: https://www.landbase.com/blog/real-cost-manual-lead-qualification-2026
    year: 2026
method: |
  Midpoint = fully-loaded SDR labor rate per BLS 2025 (41-3091 Securities/Financial Sales
  Agents ~$55/hr fully-loaded; 41-3099 Other Sales Representatives ~$45/hr fully-loaded;
  blended ~$50/hr) × 25 min average qualification time + prorated sales engagement stack
  cost. Gartner's "Sales Development Metrics" analysis and Gradient.works' 2025 B2B
  benchmarks anchor the time allocation: SDRs spend ~2 hrs/day actively selling (~41%
  on admin), yielding 4-6 quality conversations from 40-50 dials. Range reflects spread
  across mid-market B2B SaaS (low ~$20/lead) and enterprise outbound (high ~$60/lead).
last_reviewed: 2026-05-27
---

# Lead qualification

SDR or BDR work: an inbound or outbound lead arrives in your CRM, and a sales-development
rep researches the company, validates fit against ICP, scores the lead, and either books a
meeting or disqualifies. The baseline measures the cost of a human qualification at the
median mid-market B2B SaaS organization.

## What's in scope

- Manual research: company website, LinkedIn, news, basic intent signals
- ICP validation against documented criteria
- Initial outreach (1-2 messages) and disposition
- CRM data entry and pipeline scoring

## What's not in scope

- Sales-cycle work after qualification (discovery calls, demos, negotiation)
- Marketing-qualified lead (MQL) scoring before SDR touch
- Account-based marketing (ABM) campaigns at the org level

## Methodology

The $35 midpoint comes from:

1. **Direct labor cost**: BLS May 2025 blended sales-rep rate (~$50/hr fully-loaded) ×
   25 min = $21.

2. **Stack cost**: Mid-market B2B sales engagement stack (Outreach/Salesloft + ZoomInfo +
   Apollo + dialer) at ~$15K/SDR/yr prorated across ~1000 qualifications/yr = ~$15/lead.

Total midpoint ~$35. The Landbase 2026 reference cites $50-500 per qualified lead across
the B2B market; $35 sits at the lower-mid of that range, which matches mid-market SaaS.

## Override pattern

Enterprise outbound teams with senior AEs doing qualification, or teams using more
expensive data providers, should override upward. Offshore SDR pods should override
downward.

```python
j.init(
    workflow_baselines={
        "lead_qualification": {"human_cost_usd": 50.0, "human_time_minutes": 30},
    },
)
```

## Last reviewed

2026-05-27. Next review: 2027-05-27.
