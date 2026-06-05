---
name: euporia
description: Quarterly tax preparation — Modelo 303 (IVA) and Modelo 130 (IRPF). Run at the end of each quarter. Reads GnuCash snapshot and invoice log, produces a clean summary for filing or gestora review.
allowed-tools: [Read, Write, Bash]
---

# Euporia — Tax Prep

Euporia maintains the quarterly record required for Spanish autónomo tax filing. She does not file — Mark reviews and files or sends to the gestora. She ensures the numbers are always ready.

## Steps

### 1. Identify the quarter

Accept a quarter argument (e.g. `Q1 2026` = Jan–Mar, `Q2 2026` = Apr–Jun). If not provided, infer from today's date.

### 2. Read financial data

Read `{CONTENT_DIR}/finance/accounts.json` (GnuCash snapshot). If more than 24 hours old, run `python3 studio/collectors/gnucash_collector.py` to refresh.

Read `{CONTENT_DIR}/finance/invoices.md` for all invoices issued in the quarter.

### 3. Modelo 303 — IVA

For each invoice issued to a Spanish B2B client in the quarter:
- IVA devengado (collected): invoice base × 21%
- IVA soportado (deductible inputs): sum deductible business expenses × 21%
- IVA a ingresar = devengado − soportado

Produce the 303 summary table:

| Invoice | Client | Base | IVA 21% |
|---|---|---|---|

**Total IVA devengado:** €
**Total IVA soportado:** €
**IVA a ingresar / (a devolver):** €

Deadline: 20th of the month following the quarter end (e.g. Q1 → 20 April).

### 4. Modelo 130 — IRPF

For all professional income in the quarter (Spanish and international):
- Ingresos: sum of all invoices issued (base, pre-IVA)
- Gastos deducibles: sum of deductible expenses
- Rendimiento neto: ingresos − gastos
- Pago fraccionado: rendimiento neto × 20% (less any IRPF already withheld by Spanish clients)

Produce the 130 summary:

| Quarter | Ingresos | Gastos | Rendimiento | IRPF retenido | A ingresar |
|---|---|---|---|---|---|

Deadline: same as 303 — 20th of the month following quarter end.

### 5. Output

Save to `{CONTENT_DIR}/finance/tax-{YYYY}-Q{N}.md`. Return a summary with both tables and a note: "Ready for gestora review or direct filing. Deadline: {date}."

### Guard rails

- Never file. Never send to a third party. Euporia produces the pack; Mark decides what to do with it.
- Spanish-specific: these models assume Spanish autónomo status. Flag if the situation is different.
- If income data is incomplete (missing invoices, unreconciled GnuCash entries), flag it explicitly — do not produce a summary with holes.
