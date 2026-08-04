---
name: ivas-prep
description: Prepare quarterly IVA packet for the gestor — scaffold folders, download Harvest invoices, sort loose PDFs, pull expense invoices from Gmail.
allowed-tools: [Bash, Read]
---

# IVA Prep

Prepares the quarterly IVA packet for the gestor. Run once per quarter before the 20th.

## Usage

```
/ivas-prep              — current quarter
/ivas-prep Q2 2026      — specific quarter
/ivas-prep --dry-run    — preview only
```

---

## Step 1 — Determine quarter

Parse args. Default to the quarter just ended based on today's date:
- Jan-Mar → Q1, Apr-Jun → Q2, Jul-Sep → Q3, Oct-Dec → Q4
- If invoked in the first 20 days of a new quarter, default to the quarter just ended.

Quarter folder: `/media/data/Dropbox/Work/Admin/Financial/XOR i MB/{YEAR}/T{Q}-{YEAR}/`

---

## Step 2 — Run the prep script

```bash
python3 /media/data/dev/bain-studio/studio/tools/ivas-prep/ivas-prep.py \
  --quarter {Q} --year {YEAR} --gmail
```

This handles:
- Creating `Vendes/` and `Compres/{subfolders}/`
- Downloading Harvest invoice PDFs → `Vendes/`
- Sorting any loose PDFs in the quarter root
- Downloading Gmail invoice attachments to `Compres/{supplier}/` via Gmail API

Report what was created/downloaded/moved.

If `--gmail` fails with "credentials.json not found", see Step 3.

---

## Step 3 — Gmail setup (one-time, if credentials.json is missing)

Gmail download uses OAuth2 and requires a one-time setup:

1. Open Google Cloud Console: console.cloud.google.com (project: bain-studio)
2. Enable Gmail API if not already enabled
3. APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID → Desktop app
4. Download the JSON and save it as:
   `studio/tools/ivas-prep/credentials.json`
5. Re-run with `--gmail` — a browser window opens to authorise each account
6. Tokens are saved to `~/.config/bain-studio/gmail_token_*.json` for future runs

The script authenticates two accounts:
- `mark@bain.design` — Asana, Anthropic, Google Workspace, Gestor (Xavi), Movistar (forwarded from personal Gmail)
- `your-cloudways-email@example.com` — Cloudways, Crashplan

Note: Movistar bills go to `your-personal-email@example.com`. Forward them to `mark@bain.design` before running. Only the FM-prefixed invoice (~€80 business line) is claimable; MM-prefix is personal.

---

## Step 3b — Manual portal downloads

After the script, download anything not covered by Gmail:

**Movistar** (if email attachment not sufficient)
- Portal: https://www.movistar.es/ → Mi cuenta → Facturas emitidas → Facturas Legales

**Upwork fees**
- Portal: https://www.upwork.com/ > Reports > Billing Invoices
- Filter by month (max 31-day range to avoid warning)
- Download `summary-invoice.pdf` per month
- Claimable: subscription (~$19.99/month), Connects purchases; NOT service fee (10%)

**Namecheap**
- Portal: https://ap.www.namecheap.com/profile/billing/order/ (email receipts are HTML-only)

---

## Step 4 — Summary report

Print a checklist:

```
IVA Prep — Q{N} {YEAR}
========================

Vendes (invoices sent):
  [x] INVOICE_877 — Beato (€X)
  [x] INVOICE_878 — ...
  [ ] Check: invoices 881, 882 missing from Harvest?

Compres (invoices received):
  [x] Cloudways — invoice found in Gmail (Apr 7)
  [x] Anthropic — invoice found in Gmail (Apr 23)
  [ ] Movistar — not found in Gmail, check manually
  ...

Next steps:
  1. Save any Gmail attachments listed above to their Compres folders
  2. Check any [ ] items manually
  3. Send T{Q}-{YEAR}/ folder to gestor
```

---

## Notes

- Gmail download is automated via `gmail_download.py` — covers 7-day grace period after quarter end
- OAuth tokens refresh automatically — re-auth only needed if revoked
- Deadline: Mod 303 is due 20th of the month after quarter end (Q2 → 20 July)
- Full expense checklist and quarter-specific items: see `docs/Finances/iva-mod303.md`
