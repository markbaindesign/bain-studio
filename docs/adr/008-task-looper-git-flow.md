# ADR 008 — Task looper uses git flow for branch management

**Date:** 2026-06-25
**Status:** Accepted

## Decision

The task-looper skill uses `git flow feature start {slug}` to create feature branches, rather than raw `git checkout -b`. On task completion it pushes the branch and raises a PR as before — it does not call `git flow feature finish` (which would merge locally and bypass PR review).

When a task is blocked, the looper returns to the develop branch using:

```bash
git checkout "$(git config gitflow.branch.develop 2>/dev/null || echo develop)"
```

This respects however git flow is configured on the individual project.

## Context

Raw `git checkout -b feature/...` required the looper to manually track which branch to base work from (and the CLAUDE.md for this project had to explicitly document `develop` as the base). git flow encapsulates the branching convention — the develop branch, prefix, and naming are all read from the project's git flow config.

## Consequences

- git flow must be initialised on any project the looper works in (`git flow init`)
- If git flow is not initialised, the looper falls back to `git checkout develop && git pull && git checkout -b feature/{slug}`
- PRs still target the configured develop branch — the looper does not merge
- The CLAUDE.md base-branch note is now redundant but harmless
