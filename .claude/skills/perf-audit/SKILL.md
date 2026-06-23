---
name: perf-audit
description: Performance audit against a live URL using Google PageSpeed Insights. Runs mobile + desktop, surfaces Core Web Vitals, and produces a prioritised fix list (P1-P4) ordered by impact. Saves a dated markdown report to context/perf/ in the project directory.
allowed-tools: [Bash, Read, Write]
---

# Performance Audit

Run a performance audit against a live site and save a prioritised fix report.

## Steps

### 1. Identify URL and pages

Use the URL from the invocation argument. If no URL is given, read `CLAUDE.md` for a `PROJECT_URL` or site URL.

Default to the homepage plus up to 4 key pages from the project. For WordPress sites, typical pages: `/`, `/services/`, `/contact/`, a representative content page.

If `--pages` is passed explicitly, use those paths as-is.

### 2. Determine output path

```
context/perf/perf-audit-{YYYY-MM-DD}.md
```

in the current project directory.

### 3. Run the audit script

```bash
python3 /media/data/dev/bain-studio/studio/perf_audit.py {BASE_URL} \
  --pages {COMMA_SEPARATED_PATHS} \
  --output {OUTPUT_PATH} \
  --api-key $(grep GOOGLE_API_KEY /media/data/dev/bain-studio/studio/.env | cut -d= -f2)
```

The script runs PSI mobile + desktop per page. Allow 2-3 minutes for 3-4 pages. Do not interrupt.

For a single device:
```bash
# Mobile only
python3 /media/data/dev/bain-studio/studio/perf_audit.py {BASE_URL} --mobile-only ...

# Desktop only
python3 /media/data/dev/bain-studio/studio/perf_audit.py {BASE_URL} --desktop-only ...
```

### 4. Read and summarise

Once the report is saved, read it and present a summary:

- Overall performance scores (mobile / desktop) for each page
- Core Web Vitals: flag any POOR or NEEDS IMPROVEMENT ratings
- P1 fixes: list every P1 item with its estimated saving
- P2 fixes: list with savings
- P3/P4: mention count only, don't enumerate unless asked

Be specific. "Eliminate render-blocking resources on `/` (saves ~1.2s mobile)" is useful. "Performance could be improved" is not.

### 5. Offer next steps

After the summary, offer:
- Add P1 items as Asana tasks (via mirror + sync.py)
- Re-run after fixes to compare scores
- Run `/seo-audit` if SEO scores were also low

---

## Priority scale

| Level | Meaning |
|-------|---------|
| P1 | Fix immediately — directly kills LCP or blocks rendering |
| P2 | High impact — significant score or CWV improvement |
| P3 | Medium — good practice, meaningful gains over time |
| P4 | Low — nice to have, minor or informational |

---

## Notes

- Requires `GOOGLE_API_KEY` in `studio/.env` (PageSpeed Insights API — free, no billing required).
- PSI tests the live/public URL — staging must be publicly accessible or use a tunnel.
- Reports are dated and never overwritten. Run again after fixes to compare.
- Works on any public URL — not WordPress-specific.
- Mobile scores are almost always lower than desktop and are weighted more heavily by Google.
