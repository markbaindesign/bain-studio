---
tags: [utility, research, wordpress, open-source, contribution, theme-review]
god: hephaestus
description: Research report on joining the WordPress Theme Review Team — process, tools, channels, and AI review opportunity.
---

# WordPress Theme Review Team — Research Report

**Researched:** 2026-06-25
**Task:** BSTD-041

---

## TL;DR

The Theme Review Team is open to join — no application gate, just show up in Slack and start reviewing. Claude can assist with the PHP/security/license checks that make up the bulk of review work. WordPress's own AI reviewer (Gandalf) covers plugin reviews but not theme reviews — this is an open lane.

---

## How to Join

1. WordPress.org account (already have one)
2. Join Slack at `make.wordpress.org/chat` using your WordPress.org credentials
3. Join `#themereview` channel and introduce yourself
4. Subscribe to `make.wordpress.org/themes` blog

No formal application — reviewers self-select tickets and start reviewing.

---

## Review Process

1. Go to `themes.trac.wordpress.org/report/2` — lists new themes awaiting review
2. Pick a theme, comment that you're starting review
3. Set up local WP install with WP_DEBUG = true
4. Import theme unit test data
5. Install **Theme Check plugin** (required) — automated scan for common issues
6. Review code for: license compliance (GPL), security issues, PHP errors
7. Leave ticket open for author responses
8. Approve once all requirements met

**Focus areas:** license and security. Design review is explicitly not required.

---

## Tools Used

| Tool | Purpose | Notes |
|------|---------|-------|
| Theme Check plugin | Automated scan | Required for every review |
| Query Monitor | Debug PHP errors | Optional but useful |
| Debug Bar | Request inspection | Optional |
| Monster Widget | Test widget areas | Optional |
| WP Theme Unit Test | Standardised content | Import once into local install |

---

## Communication

- **Slack:** `#themereview` — main channel, find tickets, ask questions
- **Trac:** `themes.trac.wordpress.org` — ticket system for reviews
- **Blog:** `make.wordpress.org/themes` — team updates, meeting notes
- **Meetings:** Twice monthly, Tuesday 15:00 UTC in `#themereview` Slack

---

## AI Review Opportunity

WordPress launched **Gandalf** in 2026 for automated plugin reviews (triggered a 24h hold before auto-updates). Themes are not yet covered by Gandalf — the team is still fully manual.

Claude is well-suited to theme review work:
- PHP security pattern detection (XSS, escaping, sanitisation)
- GPL license header checking
- Theme Check output interpretation
- Suggesting fixes to authors

A `/wp-theme-review` skill could: download a theme zip, run Theme Check (via WP-CLI or locally), pipe output to Claude for analysis, draft a Trac comment with findings. This would make reviews faster and more thorough than manual inspection.

---

## Next Steps

**To join:** Open Slack, find `#themereview`, introduce yourself, pick a ticket from `themes.trac.wordpress.org/report/2`.

**To build tooling:** Raise a `/feature` for a `wp-theme-review` skill — takes a theme slug or zip, runs Theme Check, returns a structured review comment draft.
