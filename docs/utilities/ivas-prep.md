---
tags: [tool, skill]
command: "python3 studio/tools/ivas-prep/ivas-prep.py [--quarter N] [--year YYYY] [--gmail] [--dry-run]"
invoke: /ivas-prep
description: Quarterly IVA packet prep — scaffolds Vendes/Compres folders, downloads Harvest invoices, pulls Gmail expense receipts via API
---

# ivas-prep

Prepares the quarterly IVA packet (Mod 303) for the gestor. Run once per quarter before the 20th of the month after quarter end.

## Invoke

```bash
# Full run — scaffold + Harvest + Gmail
python3 studio/tools/ivas-prep/ivas-prep.py --quarter 2 --year 2026 --gmail

# Scaffold + Harvest only (if Gmail not yet set up)
python3 studio/tools/ivas-prep/ivas-prep.py --quarter 2 --year 2026

# As a skill (runs script + Gmail step)
/ivas-prep Q2 2026
```

## What it does

Three sequential steps:

**1. Scaffold** — creates the quarter folder structure under `$FINANCIAL_DIR/{YEAR}/T{Q}-{YEAR}/`:
- `Vendes/` — outgoing invoices
- `Compres/` — incoming expense receipts
- `Compres/{supplier}/` — one subfolder per vendor (mirrors the previous quarter's layout, or uses defaults)

**2. Harvest invoices** — fetches all Harvest invoices in the quarter date range via the Harvest API and downloads each as `INVOICE_{N}_Mark_Crawford_Bain.pdf` into `Vendes/`. Uses the public `client_key` PDF URL — no browser needed.

**3. Gmail download** (with `--gmail`) — searches both Gmail accounts for invoices from known suppliers and downloads PDF attachments directly to the correct `Compres/{supplier}/` subfolder. Skips files that already exist.

### Covered Gmail accounts and suppliers

| Account | Suppliers |
|---|---|
| `mark@bain.design` | Anthropic, Asana, Google Workspace, Gestor (Xavi), Movistar (forwarded from personal Gmail) |
| `your-cloudways-email@example.com` | Cloudways, Crashplan |

Movistar bills go to `your-personal-email@example.com` (personal) — forward them to `mark@bain.design` before running. Only the FM-prefixed invoice (~€80) is the business line; ignore MM-prefixed ones (personal).

## Gmail setup (one-time)

Requires an OAuth2 Desktop App credential from the bain-studio GCP project:

1. console.cloud.google.com → bain-studio → APIs & Services → Credentials
2. Create OAuth 2.0 Client ID → Desktop app
3. Download JSON → save as `studio/tools/ivas-prep/credentials.json`
4. Run with `--gmail` — browser opens once per Gmail account for consent
5. Tokens saved to `~/.config/bain-studio/gmail_token_*.json` — automatic refresh on subsequent runs

## Source files

- `studio/tools/ivas-prep/ivas-prep.py` — main script (scaffold, Harvest, sort)
- `studio/tools/ivas-prep/gmail_download.py` — Gmail attachment downloader (standalone or imported)
- `.claude/skills/ivas-prep/SKILL.md` — skill definition

## Config

Reads from `studio/.env` (single consolidated env file):
- `FINANCIAL_DIR` — root of the Dropbox financial tree
- `HARVEST_TOKEN`, `HARVEST_ACCOUNT_ID` — Harvest API credentials

## Notes

- `credentials.json` is gitignored — never commit it
- Gmail tokens are stored in `~/.config/bain-studio/`, not the repo
- The `--dry-run` flag previews all operations without writing any files
- Deadline: Q1 → 20 Apr, Q2 → 20 Jul, Q3 → 20 Oct, Q4 → 20 Jan

## See also

- [Financial Review](financial-review.md) — quarterly finance reporting
- [Harvest](harvest.md) — Harvest API integration notes
