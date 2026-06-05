---
name: penia
description: Cashflow projection for the next 90 days. Reads GnuCash snapshot and active project pipeline, models income against outgoings, flags break-even risk. Run monthly or when planning new work.
allowed-tools: [Read, Write, Bash]
---

# Penia — Cashflow

Penia models risk so it never actually arrives. She is not an enemy — she is a warning.

## Steps

### 1. Read the financial snapshot

Read `context/finance/accounts.json`. If more than 24 hours old, run `python3 studio/collectors/gnucash_collector.py` to refresh.

Key fields:
- `total_eur` — current bank balance
- `upcoming_30d` — bills due in the next 30 days
- `upcoming_30d_total` — total obligations next 30 days
- `balance_after_30d` — cash after 30-day obligations
- `monthly_pl_recent` — last 3 months income/expenses/net
- `breakeven_allin` — €4,115/month (all costs + owner's draw)
- `fixed_costs` — €717.38/month

### 2. Read the pipeline

Read `/media/data/dev/misc/upwork-proposals/context/portfolio/project-database.csv`. Identify active projects (no End Date or End Date in the future). For each, note expected invoice amount and approximate timing.

Read `context/finance/invoices.md` for outstanding (unpaid) invoices.

### 3. Build the 90-day projection

Model three months from today. For each month:

| Month | Expected income | Fixed costs | Variable costs | Net | Running balance |
|---|---|---|---|---|---|

- Expected income: invoices likely to be paid + new project starts
- Fixed costs: €717.38 + autónomo quota €300 = €1,017.38/month
- Variable costs: any known one-off expenses

### 4. Flag risks

- **Break-even risk**: any month where expected income < €4,115
- **Late-payment risk**: project >3 months with no interim milestone payment
- **Capacity conflict**: more than 2 concurrent projects at full capacity
- **Runway**: how many months of fixed costs remain if no new income arrives

### 5. Output

Return the projection table and a 2–3 bullet risk summary. Save to `context/finance/cashflow-{YYYY-MM}.md`.

Be direct. If month 2 looks thin, say so.
