---
name: ivas-prep
description: Prepare quarterly IVA packet for the gestor — scaffold folders, download Harvest invoices, sort loose PDFs, pull expense invoices from Gmail.
allowed-tools: [Bash, Read, mcp__claude_ai_Gmail__search_threads, mcp__claude_ai_Gmail__get_thread]
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
  --quarter {Q} --year {YEAR}
```

This handles:
- Creating `Vendes/` and `Compres/{subfolders}/`
- Downloading Harvest invoice PDFs → `Vendes/`
- Sorting any loose PDFs in the quarter root

Report what was created/downloaded/moved.

---

## Step 3 — Gmail: pull expense invoices

Search Gmail for expense invoices received during the quarter. The quarter date range:
- Q1: 1 Jan – 31 Mar
- Q2: 1 Apr – 30 Jun
- Q3: 1 Jul – 30 Sep
- Q4: 1 Oct – 31 Dec

### Known senders and their Compres subfolder

| Sender pattern | Subfolder |
|---|---|
| cloudways.com | Cloudways |
| anthropic.com | Anthropic |
| asana.com | Asana |
| github.com | Github |
| google.com / googleworkspace | Google |
| movistar.es | Movistar |
| digital-river.com / digitalriver | Crashplan |
| algolia.com | Algolia |
| namecheap.com | Namecheap |
| harvest.com / getharvest | Harvest |
| upwork.com | Upwork |
| amazon.com / amazon.es | Amazon |
| vimeo.com | Vimeo |
| gitkraken.com | Gitkraken |

Use `mcp__claude_ai_Gmail__search_threads` to search for each sender within the quarter date range. Gmail date format: `after:YYYY/MM/DD before:YYYY/MM/DD`.

Example search: `from:cloudways.com has:attachment after:2026/04/01 before:2026/07/01`

For each thread found with a PDF attachment:
1. Read the thread with `mcp__claude_ai_Gmail__get_thread`
2. Report: sender, date, subject, attachment filename
3. Note: you cannot download attachments directly — list them so Mark can save manually, or note that auto-download requires Gmail API scope beyond MCP

### What to report

For each Compres subfolder, report:
- Invoices found in Gmail (date, sender, subject, attachment name)
- Whether the subfolder already has a file (may already be downloaded)
- Subfolders with no Gmail match found (may need manual check)

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

- Gmail MCP can search and read threads but cannot download attachments as files — list them for manual download
- The script handles all file operations; this skill handles the Gmail search and final report
- Deadline: Mod 303 is due 20th of the month after quarter end (Q2 → 20 July)
