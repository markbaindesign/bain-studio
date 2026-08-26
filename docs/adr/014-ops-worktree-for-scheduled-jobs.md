---
tags: [adr, infrastructure, git, cron, deployment]
god: periphetes
description: Scheduled jobs ran from the dev checkout, so whatever branch was checked out silently decided what production did at 08:00. They now run from a separate git worktree pinned to a release tag, deployed deliberately via a script.
---

# ADR 014 - Scheduled jobs run from a release-pinned ops worktree

**Date:** 2026-08-26
**Status:** Accepted, implemented
**Related:** `docs/utilities/ops-worktree.md`, `docs/utilities/wp-pulse.md`, [ADR 009](009-studio-looper-canonical.md)

## Decision

All scheduled studio jobs run from a dedicated git worktree, not from the dev checkout:

```
/media/data/dev/bain-studio    dev checkout - whatever branch is being worked on
/home/bain/ops/bain-studio     ops worktree - detached HEAD at a release tag, cron runs here
```

The ops worktree sits on a **detached HEAD at a release tag**, never on the `main` branch.

Deploying is a **separate step from releasing**. `git flow release finish` changes nothing about
what executes at 08:00; `studio/scripts/ops-deploy.sh` does.

The 27 gitignored runtime paths - secrets, collector state, Asana mirrors, inbox, logs - are
symlinked from the ops worktree back to the dev checkout by
`studio/scripts/ops-worktree-link.sh`, so exactly one copy of each exists.

## Context

A cron entry names a **path, not a ref**. With a single checkout, `cd /media/data/dev/bain-studio`
gave cron whatever branch happened to be checked out. Dev branch state silently decided
production behaviour.

This was not theoretical. On 2026-08-26 both failure modes appeared within an hour:

- A newly built collector (`wp_pulse`) existed only on `feature/wp-pulse`. Had that branch been
  switched away from before its Thursday 08:25 run, cron would have hit a missing file and
  failed into a log nobody reads - after marking every feed entry as seen.
- Every scheduled job was, at that moment, executing from a feature branch simply because it was
  checked out. None of that code had been merged.

The same session surfaced how invisible such failures are: `gmail_watch` had crashed on **every
run since 2026-05-26** - 90 consecutive `FileNotFoundError: 'claude'` - because cron's `PATH`
lacked `~/.local/bin`. Nothing surfaced it, because a scheduled job's only witness is a log file.
An ops arrangement that fails silently is worth little; this one at least fails the same way every
time rather than depending on what was checked out.

## Reasoning

**Why a worktree and not a second clone.** A clone duplicates the object database and gives two
independent sets of refs that must `push`/`fetch` to each other. A worktree shares the object
database: a commit in one is instantly visible in the other, and the second tree costs only its
checked-out files.

**Why a detached tag and not the `main` branch.** This was got wrong first. Pinning the ops
worktree to `main` broke git flow completely: `git flow release finish` runs
`git checkout main || die "Could not check out branch 'main'."`
(`/usr/lib/git-core/git-flow-release`), and a branch can only be checked out in one worktree at a
time. Release 1.2.0 was cut with the ops tree holding `main`, and the tag landed on the release
branch instead of `main` as a result.

Detaching frees `main` for git flow and is independently better: cron runs an explicit named
version rather than "whatever `main` points at", and rollback is deploying the previous tag.

**Why state is shared rather than duplicated.** This is a correctness requirement, not tidiness.
A worktree checks out **tracked files only**, so a fresh ops tree has no collector state. Left to
diverge, `wp_pulse` would re-summarise posts the other tree had already digested, `gmail_watch`
would reprocess threads, and `careers_watch` would re-alert on known postings. Verified after
setup: `wp_pulse` from the ops tree saw 3 new posts, not 42.

**Why `looper_runner` is included.** It was initially excluded on the grounds that it "creates
branches and commits". That was wrong on both counts: it runs no git commands at all, and its
`STUDIO` path was hardcoded, so its cron working directory never determined where it operated.
Branching happens inside the claude session it launches, which resolves each task's prefix through
the registry and `cd`s to that project - so work lands in the task's **home project**, per
[ADR 009](009-studio-looper-canonical.md). The mistaken exclusion left the one unattended 02:00
job as the only thing still executing whatever branch was checked out.

## Consequences

- **Code reaches cron by being merged and deployed, never by being edited.** The convenience of
  "edit file, cron picks it up" is gone. This is the point, but it is a real cost.
- **A cut release is not a live release.** Forgetting `ops-deploy.sh` means cron keeps running the
  previous version indefinitely, with no error to signal it. `ops-deploy.sh --check` reports the
  gap.
- **The ops worktree must never be branched in, committed to, or edited.** It is a deployment
  target. `ops-deploy.sh` refuses to deploy over local modifications rather than discarding them.
- **`ops-worktree-link.sh` must be re-run** whenever a new gitignored runtime path is added that a
  scheduled job needs, or the ops tree will grow its own divergent copy. `ops-deploy.sh` does this
  automatically on every deploy.
- **Scripts must not derive the studio path from `__file__`.** From the ops tree that resolves to
  a deployment target that must not be written to. `looper_runner` resolves `STUDIO_DIR` from
  `studio/.env`, then the registry, then its own repo root, validating each candidate.
- Removing the worktree is `git worktree remove`; deleting the directory by hand leaves a stale
  registration until `git worktree prune`.
- Cron's `PATH` is set explicitly in the crontab, since its default (`/usr/bin:/bin`) contains
  neither `claude` nor `node`. This is independent of the worktree but was the other half of the
  same class of silent scheduled-job failure.
