---
tags: [tool, collector]
invoke: careers_watch.py
description: Watches target companies' careers pages for new job postings and alerts via Slack when one appears
---

# careers_watch

Tracks a dynamic list of target companies' careers pages and pings Slack (via the studio notifier) when a new job posting link appears. Diffs against a per-company snapshot of previously-seen posting links, so it only fires on genuinely new postings — not on unrelated page edits.

## Usage

```bash
python3 studio/collectors/careers_watch.py --add "Company Name" "https://company.com/careers"
python3 studio/collectors/careers_watch.py --list
python3 studio/collectors/careers_watch.py --remove company-slug
python3 studio/collectors/careers_watch.py            # run all checks (also runs on cron)
```

## Files

- Registry: `studio/collectors/careers_watch_companies.json` — the list of companies being watched
- State: `studio/collectors/careers_watch_state/{slug}.json` — per-company snapshot of seen posting links (gitignored)
- Log: `studio/collectors/careers_watch.log` (gitignored)

## Schedule

Runs twice daily via cron, 09:00 and 17:00:

```
0 9,17 * * * python3 studio/collectors/careers_watch.py >> studio/collectors/careers_watch.log 2>&1
```

## How it detects postings

**ATS API (preferred, automatic):** Greenhouse, Lever, and Workable URLs are detected by pattern and read via their public, unauthenticated JSON job-board APIs:
- Greenhouse: `boards-api.greenhouse.io/v1/boards/{slug}/jobs`
- Lever: `api.lever.co/v0/postings/{slug}?mode=json`
- Workable: `www.workable.com/api/accounts/{slug}?details=true`

This works regardless of whether the company's own careers page is JS-rendered — the API is unaffected. Add whatever URL you find for the company (e.g. `apply.workable.com/{slug}`, `boards.greenhouse.io/{slug}`, `jobs.lever.co/{slug}`) and the slug is extracted automatically.

**HTML scrape (fallback):** for any URL that doesn't match a known ATS pattern, falls back to a plain HTTP fetch + `<a>` tag extraction, matching link text/href against job-related keywords ("job", "career", "position", "opening", "apply") and filtering nav chrome. This fallback WILL fail silently (zero postings, logged as a warning) on client-rendered SPA pages with no server-rendered content — if a company isn't on a known ATS, check with `curl` first to confirm the page actually serves usable HTML before relying on it.

The first check on a newly-added company establishes a baseline silently (no alert) — only postings that appear after that baseline trigger a Slack ping.

## Source

`studio/collectors/careers_watch.py`
