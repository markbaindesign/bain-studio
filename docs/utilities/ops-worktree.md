---
tags: [utility, ops, git]
invoke: ops-worktree-link.sh
description: Dedicated git worktree pinned to main that all scheduled jobs run from, so cron never executes whatever branch happens to be checked out
---

# Ops worktree

All scheduled studio jobs run from a **separate git worktree pinned to a release tag**, not from
the dev checkout.

```
/media/data/dev/bain-studio    <- dev checkout, whatever branch you are working on
/home/bain/ops/bain-studio     <- ops worktree, detached at a release tag, cron runs here
```

The ops worktree sits on a **detached HEAD at a release tag**, not on the `main` branch. That
detail matters for two reasons, and the first was learned the hard way:

1. **git flow needs `main` free.** `git flow release finish` runs
   `git checkout main || die "Could not check out branch 'main'."` (see
   `/usr/lib/git-core/git-flow-release`). A branch can only be checked out in one worktree at
   a time, so pinning ops to `main` breaks every git flow release command. Detaching leaves
   `main` available in the dev checkout.
2. **A tag is a stronger promise than a branch.** Cron runs an explicit, named version rather
   than "whatever `main` points at right now", and rollback is just deploying the previous tag.

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
git -C /media/data/dev/bain-studio worktree add --detach /home/bain/ops/bain-studio 1.2.0
studio/scripts/ops-worktree-link.sh
```

Note `--detach` and a **tag**, not `main` - see above for why.

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

`looper_runner` stays on the dev checkout because it *creates branches and commits*. The ops
worktree is on a detached HEAD, so committing there would strand the work on no branch at all,
and branching there would move it off the deployed tag - destroying the invariant the whole
arrangement exists to protect.

## Releasing and deploying

Releasing and deploying are **two separate steps**. Cutting a release does not change what cron
runs; deploying does. That separation is the point of the arrangement.

### 1. Cut the release (normal git flow, in the dev checkout)

```bash
git flow release start 1.3.0
# update CHANGELOG.md and VERSION on the release branch, commit
git flow release finish 1.3.0        # merges to main, tags, merges back to develop
git push origin main develop
git push origin 1.3.0
```

`git flow release finish` opens an editor for the merge and tag messages. To run it
non-interactively, set `GIT_MERGE_AUTOEDIT=no` and pass `-m`:

```bash
GIT_MERGE_AUTOEDIT=no git flow release finish -m "1.3.0" 1.3.0
```

Do this in the **dev checkout**. It will fail if any worktree holds `main` - which is exactly
why the ops tree stays detached.

### 2. Deploy to the ops worktree

```bash
studio/scripts/ops-deploy.sh --check     # what would change, in either direction
studio/scripts/ops-deploy.sh             # deploy the latest tag
studio/scripts/ops-deploy.sh 1.2.0       # deploy a specific tag - this is also the rollback
```

The script fetches tags, checks out the target tag detached, re-runs `ops-worktree-link.sh`
(a new release may add runtime paths, and a checkout can leave a tracked file where a symlink
belongs), and prints the exact command to roll back to where you just came from.

It refuses to run if the ops worktree has uncommitted changes to tracked files - that means
something wrote into a tree nobody should be editing by hand, and discarding it silently would
be wrong.

**Until you deploy, cron keeps running the previous release.** That is the intended behaviour,
not a bug: `git flow release finish` alone changes nothing about what executes at 08:00.

## Rules

- **Never check out a branch in the ops worktree.** It stays detached at a release tag. Use
  `ops-deploy.sh` to move it; do not `git checkout` there by hand.
- **Never edit files in the ops worktree.** It is a deployment target. `ops-deploy.sh` will
  refuse to deploy over local modifications rather than discard them.
- Removing it: `git worktree remove /home/bain/ops/bain-studio`. Deleting the directory by hand
  leaves a stale registration until `git worktree prune`.
- Re-run `ops-worktree-link.sh` after recreating the worktree, or after adding any new
  gitignored runtime file that a scheduled job needs. `ops-deploy.sh` does this for you.

## Verifying

Reproduce cron's environment rather than trusting your shell - see the "Verifying under cron"
section of [[wp-pulse]] for why:

```bash
env -i HOME="$HOME" PATH=/home/bain/.local/bin:/home/bain/.nvm/versions/node/v22.23.1/bin:/usr/local/bin:/usr/bin:/bin \
  bash -c 'cd /home/bain/ops/bain-studio && python3 studio/collectors/wp_pulse.py --dry-run'
```

## Source

`studio/scripts/ops-worktree-link.sh`
