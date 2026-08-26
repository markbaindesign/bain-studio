---
tags: [utility, ops, git]
invoke: ops-worktree-link.sh
description: Dedicated git worktree pinned to main that all scheduled jobs run from, so cron never executes whatever branch happens to be checked out
---

# Ops worktree

All scheduled studio jobs run from a **separate git worktree pinned to `main`**, not from the
dev checkout.

```
/media/data/dev/bain-studio    <- dev checkout, whatever branch you are working on
/home/bain/ops/bain-studio     <- ops worktree, always main, cron runs here
```

## Why

A cron entry names a *path*, not a *ref*. With one checkout, `cd /media/data/dev/bain-studio`
gives cron whatever branch was last checked out - so your dev branch silently decided what
production ops did at 08:00. Two concrete failures this caused:

- A collector committed only on a feature branch vanished from cron the moment that branch was
  switched away from, failing into a log file nobody reads.
- Every scheduled job ran from a feature branch simply because it was checked out, executing
  code that was never merged.

With the ops worktree, code reaches cron by being **merged to main**, which is a deliberate act,
rather than by happening to be checked out at the right moment.

The tradeoff is real and worth stating: you lose "edit file, cron picks it up" immediacy. A
change must be merged to `main` before a scheduled job will run it.

## Setup

```bash
git -C /media/data/dev/bain-studio worktree add /home/bain/ops/bain-studio main
studio/scripts/ops-worktree-link.sh
```

A worktree checks out **tracked files only**. Everything gitignored - `studio/.env`,
`projects.json`, collector state, Asana mirrors, logs - is absent in a fresh worktree.
`ops-worktree-link.sh` symlinks all 27 such paths back to the dev checkout so there is exactly
one copy of each.

That sharing is a **correctness requirement, not tidiness**. If each tree kept its own collector
state, `wp_pulse` would re-summarise posts the other tree had already seen, `gmail_watch` would
reprocess threads, and `careers_watch` would re-alert on known postings.

```bash
studio/scripts/ops-worktree-link.sh --check     # report only, change nothing
```

The script is idempotent and refuses to clobber a real file where a symlink belongs - if the ops
tree has grown its own copy of some state, it reports a conflict and exits non-zero rather than
deleting data.

## What runs where

| Job | Tree | Why |
|---|---|---|
| `sync.py`, `hermes`, `gmail_watch`, `gnucash_collector`, `harvest_kf_collector`, `obsidian_collector`, `careers_watch`, `wp_pulse`, `account_forecast_report` | **ops** (`main`) | Read, report, collect. No branching. |
| `looper_runner.py` | **dev** | Deliberately excluded - see below. |

`looper_runner` stays on the dev checkout because it *creates branches and commits*. Running it
from a worktree pinned to `main` would either move that worktree off `main` - destroying the
invariant the whole arrangement exists to protect - or commit directly to `main`, which the git
flow forbids.

## Rules

- **Never check out another branch in the ops worktree.** It exists to be `main`. Git enforces
  the converse for you: a branch checked out in one worktree cannot be checked out in another,
  so the ops tree "owns" `main` and you inspect it from the dev tree with `git log main`.
- After merging to `main`, the ops worktree needs updating - it does not follow the branch
  automatically:
  ```bash
  git -C /home/bain/ops/bain-studio pull --ff-only
  ```
- Removing it: `git worktree remove /home/bain/ops/bain-studio`. Deleting the directory by hand
  leaves a stale registration until `git worktree prune`.
- Re-run `ops-worktree-link.sh` after recreating the worktree, or after adding any new
  gitignored runtime file that a scheduled job needs.

## Verifying

Reproduce cron's environment rather than trusting your shell - see the "Verifying under cron"
section of [[wp-pulse]] for why:

```bash
env -i HOME="$HOME" PATH=/home/bain/.local/bin:/home/bain/.nvm/versions/node/v22.23.1/bin:/usr/local/bin:/usr/bin:/bin \
  bash -c 'cd /home/bain/ops/bain-studio && python3 studio/collectors/wp_pulse.py --dry-run'
```

## Source

`studio/scripts/ops-worktree-link.sh`
