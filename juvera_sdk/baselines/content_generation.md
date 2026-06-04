---
workflow_type: content_generation
human_cost_usd: 50.0
human_cost_usd_range: [20.0, 100.0]
human_time_minutes: 30
human_time_minutes_range: [15, 75]
confidence: medium
sources:
  - title: "McKinsey — The Economic Potential of Generative AI: The Next Productivity Frontier (2023, updated 2024)"
    url: https://www.mckinsey.com/capabilities/tech-and-ai/our-insights/the-economic-potential-of-generative-ai-the-next-productivity-frontier
    year: 2024
  - title: "McKinsey — AI in the Workplace 2025"
    url: https://www.mckinsey.com/capabilities/tech-and-ai/our-insights/superagency-in-the-workplace-empowering-people-to-unlock-ais-full-potential-at-work
    year: 2025
  - title: "BLS Occupational Employment Statistics May 2025 — 27-3043 Writers and Authors, 13-1161 Marketing Specialists"
    url: https://www.bls.gov/oes/tables.htm
    year: 2025
  - title: "Sight AI — AI Content Generation Pricing 2026 (vendor; secondary illustration)"
    url: https://www.trysight.ai/blog/ai-content-generation-pricing
    year: 2026
  - title: "Engage Coders — AI vs Human Content Costs 2025 (vendor; secondary illustration)"
    url: https://www.engagecoders.com/ai-content-is-4-7x-cheaper-than-human-content/
    year: 2025
method: |
  Midpoint = mid-tier content writer / marketing specialist fully-loaded rate per BLS
  2025 (27-3043 Writers and Authors median ~$36/hr → fully-loaded $50-65/hr; 13-1161
  Marketing Specialists median ~$39/hr → fully-loaded $55-75/hr; blended ~$60/hr) × 30 min
  for a short content unit + tool / overhead cost = $50. McKinsey's "Economic Potential
  of Generative AI" (2023, updated 2024) is the analyst-firm anchor: marketing/sales is
  one of 63 priced use cases in McKinsey's $2.6-4.4T/yr value framework, and marketers
  using generative AI report saving 5+ hours per week on content creation tasks. Range
  spans short social-post or single-email copy (low, $20) and full long-form article block
  (high, $100).
last_reviewed: 2026-05-27
---

# Content generation

Producing marketing or operational copy: blog sections, social posts, product
descriptions, email body text, FAQ entries, internal newsletter copy. The baseline
measures the cost of a human marketer or writer producing one short content unit.

## What's in scope

- Short blog section (300-500 words)
- Social media post drafting (single platform)
- Email body copy (1-2 paragraphs)
- Product description (single SKU)
- FAQ entry (1-3 questions answered)

## What's not in scope

- Full long-form article (~2000 words) — multiplier; override or use a custom workflow
- Brand strategy / messaging architecture
- Video script / podcast writing
- Translation / localization

## Methodology

The $50 midpoint reflects:

- **BLS-anchored labor cost**: blended writer + marketing specialist rate ~$60/hr
  fully-loaded × 30 min = $30 raw.

- **Tool stack + revision overhead**: CMS, SEO tools, image rights, light editing pass
  prorated per content unit ~$20.

- **Total ~$50.** Aligns with Sight AI's cited editor benchmark of $50/hr.

The $20 lower bound is for tweets, internal Slack announcements, or short social posts.
The $100 upper bound is for long-form blog blocks with research and SEO optimization.

## Override pattern

Agency / freelance teams with senior copywriters (~$100/hr+) should override upward.
In-house teams with marketing-coordinator-tier staff should override downward.

```python
j.init(
    workflow_baselines={
        "content_generation": {"human_cost_usd": 75.0, "human_time_minutes": 45},
    },
)
```

## Last reviewed

2026-05-27. Next review: 2027-05-27.
