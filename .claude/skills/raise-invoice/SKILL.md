---
name: raise-invoice
description: Raise an invoice for a completed project or milestone. Invoke with a project slug or name. Produces a formatted invoice ready for review. Payment/status tracking lives in Harvest, not a local log.
allowed-tools: [Read, Write, Bash]
---

# Raise Invoice

Produces a formatted invoice for a completed project or milestone, with the correct Spanish IVA/IRPF treatment applied.

## Steps

### 1. Load the project record

Read the project row from `/media/data/dev/misc/upwork-proposals/context/portfolio/project-database.csv`. Extract:
- Client Name, Project Name, End Date
- Quoted Price, Final Price (use Final Price if set, otherwise Quoted Price)
- Upwork? field

If the project is not in Mnemosyne, stop and ask Mark to log it first via `/log-project`.

### 2. Load rate and tax configuration

Read `/media/data/Dropbox/Work/Admin/Financial/Accounting/config/rates.yaml` for: studio rate, Upwork rate, IVA rate (21%), IRPF rate (15%).

### 3. Determine tax treatment

- **Upwork project**: no IVA, no IRPF — Upwork handles this. Invoice is internal record only.
- **Spanish B2B client**: IVA 21% applies (added to invoice total). IRPF 15% applies (withheld by payer).
- **International direct client**: no IVA or IRPF.

Ask Mark to confirm the client type if it is ambiguous.

### 4. Produce the invoice

```
FACTURA / INVOICE
Número: {YYYY-NNN}
Fecha: {YYYY-MM-DD}
Vencimiento: {30 days from issue}

DE / FROM:
Mark Bain — Bain Design
mark@bain.design
NIF: [Mark's NIF]

PARA / TO:
{Client Name}
{Client address if known}

CONCEPTO / DESCRIPTION:
{Project Name} — {brief description of services}

BASE IMPONIBLE:        €{amount}
IVA 21% (if applicable): €{iva}
IRPF -15% (if applicable): -€{irpf}
TOTAL:                 €{total}

FORMA DE PAGO / PAYMENT:
Transferencia bancaria / Bank transfer
IBAN: [Mark's IBAN]
BIC: [Mark's BIC]
Referencia: {invoice number}
```

### 5. Output

Return the full invoice text. Note: "Ready for Mark's review — send via Wise or email once approved."

Do not send. Mark approves and sends. The Law of the Gate.
