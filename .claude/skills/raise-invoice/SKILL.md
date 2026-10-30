---
name: raise-invoice
description: Check uninvoiced Harvest hours and raise a Harvest draft invoice, from a project's unbilled time or as a fixed milestone. Invoke with a project name fragment or Harvest project ID, or with no args to see what is unbilled. Only ever creates drafts; Mark sends from Harvest.
allowed-tools: [Bash, Read]
---

# Raise Invoice

A thin trigger for `raise_invoice.py`. Harvest numbers the invoice, renders the PDF, sends it
and tracks payment. The script only creates **drafts**, and only with `--create`.

```
SCRIPT=/media/data/dev/bain-studio/studio/tools/raise-invoice/raise_invoice.py
python3 $SCRIPT uninvoiced [--all]
python3 $SCRIPT hours PROJECT [--from YYYY-MM-DD --to YYYY-MM-DD] [--type T] [--create]
python3 $SCRIPT milestone PROJECT --amount N --description TEXT [--type T] [--create]
```

`PROJECT` is a Harvest project ID or a fragment of an active project's or client's name (the
skill arg, if given). `--type` is `es`, `eu`, `intl` or `upwork`. Run `--help` on a subcommand
for the rest (`--currency`, `--customer-vat`, `--issue-date`, `--allow-draft`, `--summary`).

## Steps

### 1. See what is unbilled

Run `uninvoiced`. Show Mark the output, including any credits and fixed-fee rows.

### 2. Mark picks hours or milestone

- **Hours**: bills the project's unbilled time. Use `--from/--to` for part of it.
- **Milestone**: one fixed-price line. **Mark gives the amount and the description.** Never infer
  them. You may cross-check against the proposal or Asana and point out a mismatch.

Fixed-fee projects are billed by milestone, not hours.

### 3. Preview and confirm

Run the subcommand **without** `--create`. The preview shows the client, currency, type, tax,
lines and notes. Confirm with Mark:

- the type (the preview suggests one from past invoices when `--type` is missing)
- the currency (it comes from the client's last invoice of the same kind, not the client record)
- the notes, and every WARNING line

Re-run the preview with any corrected flags until Mark is happy with it.

### 4. Create the draft — only on Mark's yes

Re-run the exact previewed command with `--type` set and `--create`, and only after Mark says yes
to **that** draft. This is not reversible in the usual sense: importing time marks those hours
invoiced in Harvest at once, until the draft is deleted. Never pass `--create` speculatively.

### 5. Hand over

Give Mark the Harvest link the script prints. **Do not send.** Mark reviews the draft and sends
it from Harvest. The Law of the Gate.
