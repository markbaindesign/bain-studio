---
name: seo-audit
description: Technical SEO audit across key pages of a live site. Checks robots.txt, sitemap, per-page metadata (title, description, canonical, H1, JSON-LD, Open Graph), and Core Web Vitals via Google PageSpeed Insights API (free, no account needed). Saves a dated markdown report to context/seo/ in the project directory. Run at project start, after SEO work, or on demand.
allowed-tools: [Bash, Read, Write]
---

# SEO Audit

Run a technical SEO audit against a live site and save a dated report.

## Steps

### 1. Identify URL and pages

Use the URL from the invocation argument. Read the current project CLAUDE.md to identify key pages — course pages, landing pages, important content templates. Default to the homepage plus up to 5 project-specific pages.

If `--pages` was passed explicitly in the invocation, use those paths as-is.

Typical pages for a WordPress site: `/`, `/aren/`, `/pren/`, `/pricing-intelligence-masterclass/`, `/blog/`, `/testimonials/`

### 2. Determine output path

```
context/seo/seo-audit-{YYYY-MM-DD}.md
```

in the current project directory. The script creates the directory automatically.

### 3. Run the audit script

```bash
python3 /media/data/dev/bain-studio/studio/seo_audit.py {BASE_URL} \
  --pages {COMMA_SEPARATED_PATHS} \
  --output {OUTPUT_PATH}
```

The script takes 2–5 minutes for ~5 pages when PSI is enabled. Let it run to completion — do not interrupt.

For a fast metadata-only check (seconds, no performance scores):
```bash
python3 /media/data/dev/bain-studio/studio/seo_audit.py {BASE_URL} \
  --pages {COMMA_SEPARATED_PATHS} \
  --output {OUTPUT_PATH} \
  --no-psi
```

### 4. Read and summarise

Once the report is saved, read it and present a summary covering:
- Total blocking issue count and warning count
- Worst-performing page (lowest PSI score if available)
- Must-fix list (all blocking issues, numbered)
- Should-fix list (high-priority warnings)
- Any wins (passing checks worth noting)

Be specific. "Title too long on /aren/ (72 chars — trim to ≤60)" is useful. "Some titles need work" is not.

### 5. Offer to add blockers to backlog

If blocking issues were found, offer to add them as Asana tasks via studio-pm. Each blocker becomes one task with the specific fix described in the task body.

---

## Notes

- **PSI rate limit:** The free PSI API allows ~2 requests/second without a key. For more than 8 pages, use `--api-key` with a free Google Cloud API key — no billing required, just a Google account and a project at console.cloud.google.com.
- **`--no-psi`** skips PageSpeed entirely and runs in under 10 seconds — useful for a quick metadata check or when you only care about tags, not performance.
- **Reports are dated and never overwritten.** Run again after fixes to compare.
- **Works on any project** — not WordPress-specific. Pass any public URL.
- **Blocking issues** are things that directly harm search visibility (missing title, noindex, fetch failure). **Warnings** are best-practice gaps that hurt rankings over time.
