---
tags: [skill, utility, release]
command: /release-report
description: Generate a client-facing release report from CHANGELOG.md. Plain English, no technical jargon. Outputs a dated markdown file and optionally creates a Gmail draft.
---

# release-report — Client Release Report

Reads a version entry from `CHANGELOG.md` and produces a plain-English update for the client.

## Invoke

```
/release-report
/release-report 1.2.0
```

## What it does

1. Reads the target version from `CHANGELOG.md`
2. Translates technical entries into client-readable language
3. Saves to `docs/release-report-{version}-{YYYY-MM-DD}.md`
4. Offers to create a Gmail draft to send to the client

## Voice

Uses `$STUDIO_CONTENT_DIR/internal/brand.md` — existing client relationship register. Direct, no filler, signs off "Cheers".

## Release order

`/changelog` → **`/release-report`** → `/review-checklist` → deploy

## See also

- [changelog](changelog.md) — must run first
- [review-checklist](review-checklist.md) — run after
