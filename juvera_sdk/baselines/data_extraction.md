---
workflow_type: data_extraction
human_cost_usd: 18.0
human_cost_usd_range: [5.0, 40.0]
human_time_minutes: 12
human_time_minutes_range: [8, 23]
confidence: medium
sources:
  - title: "IDC MarketScape — Worldwide Intelligent Document Processing Software 2025–2026 Vendor Assessment"
    url: https://my.idc.com/getdoc.jsp?containerId=US53014125
    year: 2025
  - title: "IDC Market Glance — Intelligent Document Processing Software 2Q25"
    url: https://my.idc.com/getdoc.jsp?containerId=US53577125
    year: 2025
  - title: "BLS Occupational Employment Statistics May 2025 — 43-9021 Data Entry Keyers, 13-1111 Management Analysts"
    url: https://www.bls.gov/oes/tables.htm
    year: 2025
  - title: "Parseur — AI Invoice Processing Benchmarks 2026 (vendor; secondary illustration)"
    url: https://parseur.com/blog/ai-invoice-processing-benchmarks
    year: 2026
  - title: "Fluxity — AI Invoice Processing Cost Savings 2025 (vendor; secondary illustration)"
    url: https://www.fluxity.ai/blog/ai-invoice-processing-cost-savings-2025
    year: 2025
method: |
  Midpoint = analyst-tier fully-loaded rate per BLS 2025 (43-9021 Data Entry Keyers
  ~$26/hr + 13-1111 Management Analysts ~$65/hr; blended analyst-tier ~$90/hr × 12 min
  validated extraction = $18). IDC MarketScape Worldwide IDP 2025-2026 sets the analyst-
  firm anchor for this market segment, citing $8-12 saved per document automated vs.
  manual processing and invoice-cycle reduction from 12 days → 3 days. Range spans pure
  data entry (low, ~$5 — 12 min × $26/hr) and analyst-validated structured extraction
  (high, ~$40).
last_reviewed: 2026-05-27
---

# Data extraction

Structured data extraction from semi-structured documents: invoices, purchase orders,
receipts, forms, scanned PDFs, or screenshots. The baseline measures the cost of an
analyst (not a pure data-entry clerk) extracting and validating fields.

## What's in scope

- Invoice line-item extraction with validation
- Purchase-order matching against catalog
- Form-field extraction with type-checking
- Receipt parsing for expense systems

## What's not in scope

- Pure data entry (rekeying without validation) — use a lower override
- Full document understanding / summarization (use `document_review` workflow)
- ETL from APIs or structured databases (the cost model is different — this baseline
  covers human-in-the-loop document parsing)

## Methodology

The $18 midpoint reflects analyst-tier work, not pure data entry. There are two anchor
points in the industry:

1. **Per-invoice benchmark (Fluxity 2025, Parseur 2026)**: $15-40 manual cost per invoice
   for finance teams; $12.88 best-in-class benchmark per Ardent Partners.

2. **BLS-derived labor cost**: 13-1111 Management Analysts $65/hr fully-loaded × 12 min
   = $13. With ~$5 of tooling/overhead (RPA license, form-recognizer API, validation
   queue) you reach ~$18.

The $5 lower bound applies if your team uses BLS 43-9021 Data Entry Keyer rates (~$26/hr
fully-loaded). The $40 upper bound applies to complex multi-page documents requiring
significant analyst validation.

## Override pattern

If you're processing high-volume simple forms (lots of repetitive small documents),
override downward. If you're extracting from complex contracts or research papers,
override upward.

```python
j.init(
    workflow_baselines={
        "data_extraction": {"human_cost_usd": 8.0, "human_time_minutes": 6},
    },
)
```

## Last reviewed

2026-05-27. Next review: 2027-05-27.
