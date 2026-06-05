# Gestor Collector — Spec

A CLI tool that collects invoices and expenses from all sources each quarter and files them into a Dropbox folder ready for the gestor.

## Problem

Filing quarterly invoices and expenses for the gestor takes half a day of manual work: downloading PDFs from ~20 accounts, pulling Harvest invoice exports, fishing through Gmail, and organising everything into folders.

## Output

```
~/Dropbox/Gestor/2026-Q1/
  income/
    harvest-invoice-001.pdf
    harvest-invoice-002.pdf
  expenses/
    namecheap/
      namecheap_2026-01-15.pdf
    vercel/
      vercel_2026-02-03.pdf
    ...
    _unmatched/
      unknown-2026-01-22.pdf
```

- One folder per quarter, named `YYYY-QN`
- `income/` — Harvest invoices, flat
- `expenses/{supplier}/` — one subfolder per supplier
- `expenses/_unmatched/` — files the tool couldn't identify confidently

Files renamed to `{supplier}_{YYYY-MM-DD}.pdf` where possible.

## Trigger

Manual CLI:

```bash
python3 studio/gestor_collector.py            # defaults to previous quarter
python3 studio/gestor_collector.py --quarter 2026-Q1
python3 studio/gestor_collector.py --dry-run  # preview what would be collected
```

## Sources

### 1. Harvest (income)

- Auth: Harvest API token in `.env`
- Pull all invoices for the target quarter via Harvest API
- Download PDFs via Playwright (Harvest renders invoices browser-side, no clean API endpoint)
- File into `income/`

### 2. Gmail (expenses — ~10 suppliers)

- Auth: Gmail API OAuth, token cached locally
- Prerequisites: user creates a Gmail label per supplier (e.g. `invoices/namecheap`)
- Tool searches each label, filters by date range for the target quarter
- Downloads PDF attachments
- Files into `expenses/{supplier}/`
- Supplier name derived from label name

### 3. Web portals (expenses — ~10 suppliers)

- Auth: credentials fetched at runtime via `lpass show {account}` (LastPass CLI)
- Playwright automation per supplier — logs in, navigates to billing history, downloads invoices for the target quarter
- Each supplier gets its own Playwright script in `studio/gestor/portals/{supplier}.py`
- Filed into `expenses/{supplier}/`

### 4. Local dump folder (expenses — ad hoc)

- Configured path in `.env`: `GESTOR_LOCAL_DUMP=/path/to/folder`
- Tool reads all PDFs in the folder
- For each file: attempt date + supplier extraction in order:
  1. Filename parsing (regex for dates, known supplier name fragments)
  2. PDF text extraction (`pdfplumber`)
  3. LLM extraction (Claude API) — passes first 500 chars of PDF text, asks for `{supplier, date}` JSON
- Files with confidence ≥ threshold go to `expenses/{supplier}/`
- Files below threshold go to `expenses/_unmatched/`
- Successfully filed files are moved out of the dump folder (or optionally archived)

## Stack

| Concern | Library |
|---|---|
| PDF download / portal login | Playwright |
| PDF text parsing | pdfplumber |
| LLM extraction | Anthropic Claude API (Haiku — cheap, fast) |
| Gmail | google-api-python-client |
| Harvest | requests (REST API) |
| Credentials | `lpass` CLI subprocess calls |
| Config | `.env` via python-dotenv |

## Config (`.env` additions)

```
HARVEST_ACCOUNT_ID=
HARVEST_API_TOKEN=
GESTOR_DROPBOX_PATH=~/Dropbox/Gestor
GESTOR_LOCAL_DUMP=~/Documents/invoices
GMAIL_CREDENTIALS_PATH=~/.config/gestor/gmail_credentials.json
ANTHROPIC_API_KEY=
```

## Supplier registry

A `studio/gestor/suppliers.json` file maps each supplier to its source type and config:

```json
[
  { "name": "namecheap", "source": "gmail", "gmail_label": "invoices/namecheap" },
  { "name": "vercel",    "source": "portal", "lpass_entry": "vercel.com", "portal_script": "vercel" },
  { "name": "harvest",   "source": "harvest" }
]
```

New suppliers added here — no code changes needed for Gmail sources, one new portal script for portal sources.

## Run output

```
Gestor Collector — 2026-Q1
==========================
income/        3 invoices from Harvest
expenses/
  namecheap/   2 invoices (Gmail)
  vercel/      1 invoice (portal)
  adobe/       1 invoice (portal)
  ...
  _unmatched/  2 files — review manually

Total: 24 files → ~/Dropbox/Gestor/2026-Q1/
Done in 4m 12s
```

## Prerequisites (one-time setup)

1. Install LastPass CLI: `sudo apt install lastpass-cli` + `lpass login mark@bain.design`
2. Create Gmail labels: one per supplier under `invoices/`
3. Run Gmail OAuth flow: `python3 studio/gestor_collector.py --auth-gmail`
4. Add suppliers to `suppliers.json`
5. Write a Playwright script for each portal supplier

## Phases

**Phase 1 — Core plumbing**
- CLI scaffold, quarter resolution, output folder creation
- Harvest income collector
- Gmail attachment collector
- Local dump collector (filename + PDF parsing + LLM fallback)

**Phase 2 — Portal collectors**
- LastPass CLI integration
- Playwright base class
- Portal scripts for top 5 accounts by invoice frequency

**Phase 3 — Remaining portals + polish**
- Remaining portal scripts
- `--dry-run` mode
- Summary report
