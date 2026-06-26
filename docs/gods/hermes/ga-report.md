---
tags: [skill, analytics, reporting, client-deliverable, ga4]
god: hermes
invoke: /ga-report
description: Pull GA4 data for a client project and compile a branded benchmark report with action points. Authenticates via service account, fetches standard metrics (sessions, users, channels, pages, devices), generates period-over-period comparisons, writes a client-ready markdown report, and outputs a branded PDF via brand-doc.
---

# GA Report

Generates a Google Analytics 4 benchmark report for a client project and brands it for handoff.

## Usage

```
/ga-report NORE
/ga-report NORE --property 542141660
/ga-report NORE --days 30
```

## What it produces

- **Executive summary** — 3-5 bullet headline findings with numbers
- **KPI table** — sessions, users, pageviews, engagement rate, bounce rate, avg. session duration with period-over-period change
- **Traffic by channel** — organic, direct, referral, social, email with share %
- **Top 10 pages** — by sessions with engagement and duration
- **Device and country breakdown**
- **Key events** (if configured) — form submits, CTA clicks, etc.
- **5-8 action points** — prioritised [HIGH/MEDIUM/LOW] with specific recommendations

Output: markdown report + branded PDF via `/brand-doc`.

## Auth setup (one-time)

Requires a Google service account with viewer access on the GA4 property.

1. Enable Google Analytics Data API in Google Cloud Console
2. Create a service account, download the JSON key
3. Add the service account email as Viewer: GA4 → Admin → Property Access Management
4. Set `GOOGLE_SA_JSON=/path/to/sa.json` in `studio/.env`

Recommended key location: `~/.config/bain-studio/google-sa.json`

## Data source

`studio/collectors/ga4_report.py` — authenticates via service account JWT (uses `cryptography` lib), calls the GA4 Data API, and returns structured JSON.

## Output location

`$STUDIO_CONTENT_DIR/reports/{project-slug}/ga-benchmark-YYYY-MM-DD.md`

## Known project property IDs

| Project | GA4 Property ID |
|---------|----------------|
| NORE | 542141660 |
