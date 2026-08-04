---
name: income-add
description: >
  Quick-add an expected incoming payment to the cash flow forecast
  (/media/data/Dropbox/Work/Admin/Financial/Accounting/config/expected_income.yaml). Trigger phrases: "expecting a payment",
  "income coming in", "add expected income", "/income-add".
---

# Income Add

Appends one entry to `/media/data/Dropbox/Work/Admin/Financial/Accounting/config/expected_income.yaml`, which Cashflow Projection/Financial Review
and the dashboard's cash flow forecast read on every run.

## Steps

1. Parse from the prompt (or ask for whatever's missing):
   - **Label** — client/project or description
   - **Amount** — numeric
   - **Currency** — default EUR if unstated
   - **Date** — expected arrival date (YYYY-MM-DD). Resolve relative phrases ("the 15th",
     "end of month", "next Friday") against today's date.
   - **Account** — which account it'll land in: BBVA EUR / Wise Business (USD) /
     Wise Business (GBP) / Unknown. Ask if not obvious from context (e.g. Upwork clients
     land in Wise Business USD via the Funds Upwork holding account; Spanish B2B clients
     land in BBVA EUR).
   - **Confidence** — `confirmed` (invoice sent / date agreed) or `estimated` (rough guess).
     Default to `estimated` unless Mark says otherwise.

2. Read the current YAML, append the new entry to the `income` list, write it back.
   Never remove or rewrite existing entries — append only.

3. Confirm what was added in one line:
   > Added: €[amount] from [label], expected [date] → [account] ([confidence])

## Rules

- Never invent an amount, date, or client — ask if any are missing from the prompt.
- This file is read by `gnucash_parser.py`'s cash flow forecast on every dashboard/collector
  run — entries with a past date are automatically ignored, no cleanup needed.
- To remove or correct an entry, edit the YAML directly (there's no "remove" mode here —
  keep it simple, it's a short manually-curated list).
