---
tags:
  - skill
  - utility
  - seo
command: /seo-audit
description: Technical SEO audit — robots.txt, sitemap, per-page metadata, and Core Web Vitals via PageSpeed Insights API. Saves a dated markdown report.
---

# seo-audit — Technical SEO Audit

Runs a technical SEO audit against a live site. Checks robots.txt, sitemap, per-page HTML metadata (title, description, canonical, H1, JSON-LD, Open Graph), and Core Web Vitals via Google PageSpeed Insights.

## Invoke

```
/seo-audit
```

Run from inside the client project directory. Reads CLAUDE.md for the site URL.

## Output

`context/seo/seo-audit-{YYYY-MM-DD}.md` — saved in the project directory, never overwritten. Run again after fixes to compare.

## Prerequisites

- Site must be publicly reachable
- `GOOGLE_API_KEY` in `.env` for PSI scores (free, no billing — see BSTD-036)
- Without the key: falls back to unauthenticated PSI (rate-limited at ~2 req/s)

## Flags

| Flag | Effect |
|---|---|
| `--no-psi` | Skip PageSpeed Insights — metadata only, runs in seconds |
| `--pages /a/,/b/` | Override the default page list |
| `--api-key KEY` | Pass key inline instead of via .env |

## Script

`studio/seo_audit.py` — callable directly:

```bash
python3 studio/seo_audit.py https://example.com --pages /,/about/ --output context/seo/audit.md
```

## See also

- [aura](../gods/aura/aura.md) — interprets audit output and sets strategy
- BSTD-036 — Google Cloud API key setup (PSI + GSC APIs)
