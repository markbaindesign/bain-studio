# ADR 009 — studio-looper is the canonical looper; task-looper deprecated

**Date:** 2026-07-22
**Status:** Accepted
**Supersedes:** ADR 008. ADR 007 (logging) is inherited unchanged.

## Decision

The studio runs **one** looper: `studio-looper`, working the cross-project **Studio Looper**
Asana project (SL) via the workspace-level **Looper Status** enum field. The per-project
`task-looper` skill is deprecated - its SKILL.md is now a redirect stub and it must not be
used to work tasks.

## Architecture (as built, 2026-07)

- **Queue:** tasks from any studio project are multi-homed into SL by Mark. sync.py preserves
  foreign Local IDs (`PRESERVE_FOREIGN_IDS`), so the looper routes each task to its home
  project directory by prefix. Tasks with no Looper Status default to Queue on next sync.
- **Statuses:** Queue → In Progress → Review | Blocked. The looper never marks a task done;
  Review and Done are Mark's. Blocked reassigns to Mark with a comment.
- **Driver:** `studio/scripts/looper_runner.py` ralph-loops
  `claude --dangerously-skip-permissions --model haiku -p '/studio-looper --yes'` until the
  queue is empty, no progress is made, or the quota window ends. The runner (not a stop hook)
  owns the iteration loop because `-p` mode exits after one result regardless of hook block
  decisions. A nightly cron window runs at 02:00; an empty queue is detected after pre-sync
  and skips the claude session entirely.
- **Git:** all work lands on a local `looper/{LOOPER_RUN_ID}` branch, one commit per task,
  base branch restored afterwards. **Never pushed, never merged** - review and merge are
  Mark's decisions at the Review gate. This supersedes ADR 008 (git flow feature branch,
  push, PR), whose flow produced unreviewed pushes to shared branches.
- **State:** session-scoped state files in `/tmp/studio-looper/`, disposable - the queue
  always rebuilds from Looper Status. A concurrency guard refuses a second live run against
  the same queue.
- **Logging:** ADR 007 conventions carried over verbatim - `~/logs/task-looper.log`
  (name kept for log continuity), sync.log line format, `[PREFIX]` tags.

## Context

task-looper (June 2026) proved the loop concept per-project but split the studio's attention:
two skills, two queue semantics, and **conflicting git rules** - ADR 008 said "push the
feature branch and raise a PR" while studio-looper's hardening (session-scoped state,
re-stamp gate, no-push enforcement hook, run review branch) settled on local-only branches.
Both rulebooks stayed live, and on 2026-07-22 a manually launched looper run pushed
`develop` directly - the old behaviour surfacing through the deprecated path.

## Known gap (closed 2026-07-22)

The no-git-push PreToolUse hook was originally armed only by `LOOPER_RUN_ID`, which the
runner sets - a manually launched `/studio-looper` ran **without** push enforcement and
relied on the skill text alone, which is how the 2026-07-22 `pushed develop` violation
happened. The hook (now versioned at `.claude/hooks/looper-no-push.sh`, symlinked into
`~/.claude/hooks/`) additionally arms when the calling session owns a looper state file
in `/tmp/studio-looper/` - written at Step 3 of every looper run, manual or scheduled -
so all looper sessions are enforced and interactive sessions remain unaffected.

## Consequences

- One queue, one set of rules, one place to harden.
- `/task-looper` still resolves but only redirects - muscle memory gets a pointer, not a run.
- Per-project targeted runs are expressed by queueing only that project's tasks in SL,
  not by a separate skill.
