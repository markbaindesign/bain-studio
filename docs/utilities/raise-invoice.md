---
description: Check uninvoiced Harvest hours and raise Harvest draft invoices from hours or as a milestone
command: python3 studio/tools/raise-invoice/raise_invoice.py {uninvoiced|hours|milestone}
invoke: /raise-invoice
role: Finance
tags:
- utility
- skill
---

# raise-invoice

Lists billable Harvest hours not yet on an invoice, and raises **draft** invoices in Harvest,
either importing a project's unbilled time or as one fixed-price milestone line. Harvest does the
numbering, PDF, sending and payment tracking. The tool never sends an invoice or marks it sent.

## Invoke

```bash
python3 studio/tools/raise-invoice/raise_invoice.py uninvoiced [--all]
python3 studio/tools/raise-invoice/raise_invoice.py hours PROJECT [--from D --to D] [--type T] [--create]
python3 studio/tools/raise-invoice/raise_invoice.py milestone PROJECT --amount N --description TEXT [--type T] [--create]

# As a skill (walks the preview → confirm → create gate)
/raise-invoice [project]
```

`PROJECT` is a Harvest project ID or a fragment of an active project's or client's name.
Needs `HARVEST_TOKEN` and `HARVEST_ACCOUNT_ID` in `studio/.env`. Reuses
`studio/dashboard/harvest_client.py`.

## Commands

- **uninvoiced** — the Harvest uninvoiced report for the last year, split into hourly ready to
  bill, hourly partly invoiced, fixed fee (the amount is the unbilled part of the fee) and credits
  (deposits or overpayments to offset). Rows under 0.25 h are hidden unless `--all`.
- **hours** — previews a draft that imports the project's unbilled time, grouped by task
  (`--summary` changes that). Warns about credits, fixed-fee projects and zero-rate entries.
- **milestone** — previews a draft with one line for `--amount` (net, before tax) and
  `--description`.

`hours` and `milestone` only preview. `--create` makes the draft, and needs an explicit `--type`.
It refuses if the client already has a draft unless `--allow-draft`.

**`--create` is never a dry run.** Importing time onto a draft marks those hours invoiced in
Harvest straight away, until the draft is deleted.

## Client types

| `--type` | Tax | Notes |
|---|---|---|
| `es` | IVA 21%, IRPF -15% (imported lines are re-flagged as taxed) | reference line + payment details |
| `eu` | none | reverse-charge block with both VAT numbers + payment details |
| `intl` | none | reference line + payment details |
| `upwork` | none | "WordPress development services via Upwork - period"; keeps a reverse-charge block if the client has one |

Without `--type` the preview suggests one from the client's past invoices. The payment-details
block and the studio's VAT number are copied from recent invoices. `--customer-vat` supplies the
customer's VAT number when none is on file.

Currency comes from the client's last invoice of the same kind (Upwork or direct), because the
Harvest client record is not always right. The preview warns when the two disagree;
`--currency` overrides.

## Tests

```bash
python3 -m pytest studio/tests/test_raise_invoice.py
```

Covers the pure helpers. Nothing in the tests calls Harvest.
