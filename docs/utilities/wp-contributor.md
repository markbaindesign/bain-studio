---
tags: [utility, research, wordpress, open-source, contribution, gutenberg]
god: hephaestus
description: Research report on AI-assisted WordPress contribution - issue feeds, process, and factory pattern. Gutenberg GitHub PRs identified as the best entry point.
---

# WordPress Contribution — Research Report

**Researched:** 2026-06-23  
**Task:** BSTD-024  
**Project spec:** ~/Dropbox/Work/Studio/context/specs/drafts/wp-contributor-spec.md

---

## TL;DR

Gutenberg (GitHub) is the best entry point for AI-assisted WordPress contribution. Issues are fully queryable via GitHub API, the PR flow is standard, CI catches regressions automatically, and `Good First Issue` labels provide a clear starting queue. Core Trac (SVN) is accessible but dated. Docs and Enhancement issues are the lowest-risk starting category.

---

## Issue Trackers

**Gutenberg — GitHub (`WordPress/gutenberg`)**

- Label: `Good First Issue`
- GitHub API: fully accessible without auth
- Current open count: ~55 (23 unassigned)
- Issue types available: Enhancement (most common), Developer Docs, Automated Testing, Bug, Build Tooling
- Issue bodies are well-structured — description, reproduction steps, acceptance criteria

```bash
gh issue list \
  --repo WordPress/gutenberg \
  --label "Good First Issue" \
  --state open \
  --json number,title,body,labels,assignees
```

**WordPress Core — Trac (`core.trac.wordpress.org`)**

- Keyword: `good-first-bug`
- RSS feed exists (`?format=rss`) but bot-blocked (403 without a browser UA)
- XML-RPC API requires a WordPress.org account
- Workflow is SVN-based (create a `.diff`, attach to ticket, set `has-patch`)
- Less suitable for automation than GitHub

---

## Contribution Types

| Type | Repo | AI suitability | Notes |
|------|------|----------------|-------|
| Gutenberg PR | GitHub (JS/React) | Best | Standard PR flow, CI, `Good First Issue` labels |
| Core patch | Trac (PHP/SVN) | Good | Dated workflow, patch format is straightforward |
| Developer docs | GitHub or make.wp.org | Very good | Low risk, always welcome |
| Automated tests | GitHub (Jest/Playwright) | Good | Clear pass/fail criteria |
| Translations | translate.wp.org | Low | Different toolchain, no code |

---

## Process — Gutenberg PR (recommended)

1. Fetch open `Good First Issue` list via GitHub API
2. Score by type and complexity - prefer Enhancement + Docs for first passes
3. Fork `WordPress/gutenberg`, clone locally
4. `npm install && npm run build`
5. Make the change; write a Jest unit test (required for logic changes)
6. PR to `trunk` - CI runs lint, unit, and e2e automatically
7. Address reviewer feedback (typically 1-2 rounds)
8. Committer merges - ships in next Gutenberg release, then into WordPress core

**Acceptance criteria:** PHPCS (PHP), ESLint (JS), unit tests for logic, accessibility for UI, inline docs for new functions.

---

## Process — Core Trac Patch

1. Find `good-first-bug` ticket
2. Set up with `wp-env` (Docker-based WP dev environment)
3. Make change against SVN checkout or git mirror
4. `svn diff > {ticket}.diff`
5. Attach diff to ticket, set status `has-patch`
6. Wait for component maintainer review

---

## AI-Assisted Factory Pattern

| Step | Who |
|------|-----|
| Fetch and score `Good First Issue` list | Claude (GitHub API) |
| Navigate codebase, understand context | Claude |
| Write the fix or feature | Claude |
- Write Jest/PHPUnit tests | Claude |
| Write PR description | Claude |
| Run PHPCS/ESLint, fix violations | Claude |
| Submit PR | Mark (PRs must be under his GitHub identity) |
| Respond to reviewer feedback | Claude + Mark |

**Hard constraint:** WordPress.org account and GitHub fork must belong to Mark. PRs cannot be submitted as bainbot - open-source contributions need a human identity.

---

## Prior Art

Mark contributed to a WordPress plugin called Shutter (noted 2026-06-15). This establishes familiarity with the GitHub PR contribution flow and builds trust with maintainers over time.

---

## Recommendation

Start with Gutenberg `Good First Issue` - specifically Enhancement or Developer Documentation type. These are low-risk, well-scoped, and the GitHub API makes issue discovery fully automatable. Build the factory as a scheduled agent: fetch → score → branch → implement + test → PR draft → notify Mark for submit.

See project spec for implementation plan.
