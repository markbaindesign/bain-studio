---
tags: [tool, collector]
invoke: careers_watch.py
description: Watches target companies' careers pages and creates an Asana task in Prospecting for each new job posting
---

# careers_watch

Tracks a list of target companies' careers pages and creates a task in the Asana Prospecting project for each new job posting: assigned to Mark, in NEXT UP, Prospect Category "Real Jobs", Job URL set. Written through `sync.py`'s `create_task` on the bainbot token. It replaces checking a careers page by hand on a repeating task. Diffs against a per-company snapshot of previously-seen posting links, so it only fires on genuinely new postings — not on unrelated page edits.

## Usage

```bash
python3 studio/collectors/careers_watch.py --add "Company Name" "https://company.com/careers"
python3 studio/collectors/careers_watch.py --list
python3 studio/collectors/careers_watch.py --remove company-slug
python3 studio/collectors/careers_watch.py            # run all checks (also runs on cron)
python3 studio/collectors/careers_watch.py --dry-run  # say what would be created; create and save nothing
```

## Files

- Registry: `~/.config/bain-studio/careers_watch_companies.json` — the companies being watched. Outside the repo because the repo is public; shared by the dev and ops checkouts. Override with `CAREERS_WATCH_REGISTRY`.
- Asana destination: `CAREERS_WATCH_PROJECT_GID`, `_SECTION_GID`, `_CATEGORY_FIELD`, `_CATEGORY_OPTION`, `_URL_FIELD` in `studio/.env`
- State: `studio/collectors/careers_watch_state/{slug}.json` — per-company snapshot of seen posting links (gitignored). Override with `CAREERS_WATCH_STATE_DIR`.
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

The first check on a newly-added company establishes a baseline silently (no task); only postings that appear after it create tasks. "First check" means the company has never been checked, not that it has nothing on record, so a company whose board empties still gets a task for its next posting. A posting is marked seen only once its task exists: if creation fails, the next run tries again.

## Source

`studio/collectors/careers_watch.py`
