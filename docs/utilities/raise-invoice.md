---
description: Check uninvoiced Harvest hours and raise Harvest draft invoices from hours or as a milestone
command: python3 studio/tools/raise-invoice/raise_invoice.py {uninvoiced|invoices|hours|milestone|expense}
invoke: /raise-invoice
god: financial-review
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
python3 studio/tools/raise-invoice/raise_invoice.py invoices [CLIENT] [--from D] [--to D] [--state S]
python3 studio/tools/raise-invoice/raise_invoice.py hours PROJECT [--from D --to D] [--type T] [--create]
python3 studio/tools/raise-invoice/raise_invoice.py milestone PROJECT --amount N --description TEXT [--type T] [--create]
python3 studio/tools/raise-invoice/raise_invoice.py expense PROJECT --amount N --category C --notes TEXT [--date D] [--receipt FILE] [--create]

# As a skill (walks the preview → confirm → create gate)
/raise-invoice [project]
```

`PROJECT` is a Harvest project ID, an active project's code (`KFX`), or a fragment of an active
project's or client's name. A code match wins over a name fragment.
Needs `HARVEST_TOKEN` and `HARVEST_ACCOUNT_ID` in `studio/.env`. Reuses
`studio/dashboard/harvest_client.py`.

## Commands

- **uninvoiced** — the Harvest uninvoiced report for the last year, split into hourly ready to
  bill, hourly partly invoiced, fixed fee (the amount is the unbilled part of the fee) and credits
  (deposits or overpayments to offset). Rows under 0.25 h are hidden unless `--all`.
- **invoices** — invoices already raised, oldest first: number, issue date, client, amount,
  state, the dates sent and paid, what is still owed, and `recurring` when a recurring schedule
  generated it. `CLIENT` is a Harvest client ID or name fragment; `--from`/`--to` filter on issue
  date. Read-only. This is how an agent checks that an invoice went out: the token stays in
  `studio/.env`, which no session reads directly.
- **hours** — previews a draft that imports the project's unbilled time, grouped by task
  (`--summary` changes that). Warns about credits, fixed-fee projects and zero-rate entries.
- **milestone** — previews a draft with one line for `--amount` (net, before tax) and
  `--description`.

- **expense** — logs a reimbursable expense (a plugin licence, hosting, stock images) on a
  project, so it lands on the client's next invoice. `--category` is an expense category ID or
  name fragment (`plugin` for Premium Plugin); `--receipt` attaches a PDF or image; `--date`
  defaults to today; `--non-billable` keeps it off the invoice. The preview shows the client's
  currency, which is the currency Harvest records the amount in: convert a receipt in another
  currency first. It warns about an expense already on the project within 60 days with the
  same amount on the same day, or the same amount and the same first word in the notes, and
  `--create` refuses on one unless `--allow-duplicate`.

`hours`, `milestone` and `expense` only preview. For invoices `--create` makes the draft, and needs an explicit `--type`.
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
