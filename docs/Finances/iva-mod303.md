---
tags: [finance, checklist, taxes]
god: plutus
description: Quarterly IVA (Mod 303) preparation process — vendes, compres, what's automated, what needs manual download, and how to send to gestor
---

# Quarterly IVA (Mod 303) — Preparation Guide

Mod 303 is the Spanish quarterly VAT return. Filed four times a year: Q1 (Jan-Mar), Q2 (Apr-Jun), Q3 (Jul-Sep), Q4 (Oct-Dec). Deadline is the 20th of the month following the quarter end (Q2 → 20 July).

The pack is prepared and sent to gestor Xavi Oliveres (`gestor@example.com`). He files it.

---

## Automated prep

Run the ivas-prep tool first. It handles scaffolding, Harvest invoices, and most Gmail receipts:

```bash
python3 studio/tools/ivas-prep/ivas-prep.py --quarter 2 --year 2026 --gmail
```

Or via skill: `/ivas-prep Q2 2026`

This downloads invoices for: Cloudways, Asana, Google Workspace, Anthropic, Gestor (Xavi's own invoice), Movistar (from forwarded emails), Crashplan. See [ivas-prep.md](../utilities/ivas-prep.md) for full detail.

---

## Vendes (outgoing invoices)

Harvest invoices are downloaded automatically. After the script runs, verify:

- [ ] All Harvest invoices for the quarter are present in `Vendes/`
- [ ] Invoices cover the whole quarter (check date range)
- [ ] Invoices are numbered and in order
- [ ] Check Upwork income — if any Upwork projects ran this quarter, confirm client invoices were raised
- [ ] Check affiliate income (if any)
- [ ] Check VIEs if required (intra-EU sales to VAT-registered businesses)

---

## Compres (incoming expense receipts)

### Automated via gmail_download.py

These are downloaded automatically when the script runs with `--gmail`:

| Supplier | Gmail account | Notes |
|---|---|---|
| Anthropic/Claude | mark@bain.design | Billing emails |
| Asana | mark@bain.design | Billing emails |
| Google Workspace | mark@bain.design | Billing emails |
| Gestor (Xavi) | mark@bain.design | `from:gestor@example.com subject:factura` |
| Movistar | mark@bain.design | Forwarded from your-personal-email@example.com — only download FM prefix (business invoice, ~€80); MM prefix is personal |
| Cloudways | your-cloudways-email@example.com | Billing emails |
| Crashplan | your-cloudways-email@example.com | "Your receipt from CrashPlan Group LLC" |

### Manual portal downloads

These cannot be pulled from email — must be downloaded from each supplier's portal:

**Movistar** (if email attachment not sufficient)
- Portal: https://www.movistar.es/ (login with NIF)
- Go to Mi cuenta > Facturas emitidas
- Download "Facturas Legales" PDF
- Save to `Compres/Movistar/`
- Only claim the FM-prefixed invoice (~€80 business line); the MM-prefixed one is personal

**Upwork fees**
- Portal: https://www.upwork.com/ > Reports > Billing Invoices (or Transaction History)
- Filter by month (not quarter — date range warning above 31 days)
- Download `summary-invoice.pdf` for each month
- Claimable: monthly subscription (~$19.99/month), Connects purchases (e.g. $30, $37.50)
- Service fee (10%) has no separate invoice — not claimable
- VAT reverse charge applies; NIE REDACTED_NIE is on file with Upwork

**Namecheap**
- Portal: https://ap.www.namecheap.com/profile/billing/order/
- Email receipts are HTML-only — must download PDF from portal
- Save to `Compres/Namecheap/`

**Autonomos**
- Social security contribution (€300/month)
- No invoice to download — confirm payment via bank statement or Seguridad Social portal

### Quarter-specific expenses

**T-1 only (Q1, Jan-Mar):**
- GitKraken (annual)
- Harvest (annual, renews Feb) — Settings > Account Settings > Billing Information > See all receipts > Download as PDF
- Vimeo (annual)
- Forecast (annual)

**T-2 only (Q2, Apr-Jun):**
- (none currently)

**T-3 only (Q3, Jul-Sep):**
- WPML (annual, renews 3 July)
- Lastpass (annual, renews 30 Sep)

**T-4 only (Q4, Oct-Dec):**
- Dropbox (annual)
- FontAwesome (annual)

### Other periodic expenses

Check each quarter whether any of these apply:

- **Meals / travel** — if for client work
- **Art supplies / office (IKEA)**
- **Amazon** — office or professional purchases
- **Algolia** — https://dashboard.algolia.com/account/billing/invoices
- **Creative Market** — https://creativemarket.com/account/purchases
- **Envato / ThemeForest** — invoices come by email at time of purchase
- **OpenAI** — https://platform.openai.com/settings/organization/billing/history
- **Payroll** — Upworkers, contractors
- **Bank fees** — check for Dec / de la Renta (Feb)

---

## Sending to Xavi

Once Vendes and Compres are complete:

1. Zip the full `T{Q}-{YEAR}/` folder
2. Email to `gestor@example.com`
3. Subject: `IVA T{Q}-{YEAR} — Mark Bain`
4. Deadline: 20th of the month after quarter end

---

## See also

- [ivas-prep tool](../utilities/ivas-prep.md) — the automation script and skill
- [Plutus](../gods/plutus/plutus.md) — quarterly finance reporting god
