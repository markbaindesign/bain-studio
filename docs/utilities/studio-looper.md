---
tags: [skill, tool]
god: hermes
invoke: /studio-looper
description: Cross-project task queue — works BainBot tasks from any studio project in Asana drag order, handing completed work to Mark for review
---

# studio-looper

Cross-project task queue. BainBot works tasks from multiple Asana projects in the order Mark
sets in the Studio Looper Asana project. Completed work moves to Review — Mark approves before
marking done.

## Invoke

```bash
/studio-looper                    # start the queue
/studio-looper --for 2h           # run for up to 2 hours
/studio-looper --use 10%          # consume at most 10% of quota
/studio-looper --yes              # skip queue confirmation
/studio-looper --at 20:00         # schedule for 20:00 today
/studio-looper --dry-run          # show queue without working tasks
/studio-looper --test             # run against the sandbox SLT queue instead of SL
```

Flags combine: `/studio-looper --at 20:00 --for 2h`, `/studio-looper --test --yes`

Must be invoked from `/media/data/dev/bain-studio`.

## How it works

1. Mark multi-homes tasks from any project (MCF, NORE, BSTD, PIPE…) into the **Studio Looper**
   Asana project, Queue section. Drag order = execution priority.
2. `/studio-looper` syncs the SL project, reads the Queue, and presents the list for
   confirmation before starting.
3. BainBot works each task in the correct project directory (derived from the task's prefix —
   MCF-007 → MCF project path, etc.).
4. On completion: task moves to **Review** section, reassigned to Mark. Task is NOT marked
   done in Asana.
5. On blocker: task moves to **Blocked** section, reassigned to Mark with a note.
6. Mark reviews tasks in the Review section, marks them done himself.

## Permission/access failures never halt the loop

A permission-denied on Edit/Write/Bash (missing `additionalDirectories` entry for the task's
project, git auth failure, sandboxed path, etc.) is treated exactly like any other blocker: log
a WARNING to `~/logs/task-looper.log`, mark the task Blocked with the access error as the reason,
sync, and advance to the next task. The loop must never stop and wait for interactive approval
mid-run — that defeats the point of running unattended.

This only fully holds when denials come back as a **scripted** decision (e.g. a PreToolUse hook
returning `permissionDecision: "deny"` with a reason) rather than an **interactive** permission
prompt, since only the former returns an error the model can react to — an interactive prompt
genuinely blocks on a human. Practical mitigation: keep `additionalDirectories` and the explicit
`Edit()` allow rules in `.claude/settings.json` complete for every registered project, so paths
the looper legitimately needs hit an allow (or a scripted deny) rather than an ambiguous ask.

## Looper Status field values

| Value | Meaning |
|---|---|
| Queue | Waiting to be worked — tasks default here automatically |
| In Progress | BainBot is currently working this |
| Blocked | Blocker found; assigned back to Mark |
| Review | Work done; Mark to review and close |
| Done | Mark confirmed; task complete |

Tasks added to the Studio Looper project with no Looper Status are automatically pushed to "Queue" by sync.py on the next sync run.

## State file

`.claude/studio-looper.{session_id}.local.md` in the studio root — **session-scoped**, named
from `$CLAUDE_CODE_SESSION_ID` at creation time (Step 3 of the skill). Written by the skill,
read and advanced by the hook. Queue entries are bare task IDs (`MCF-007`, `NORE-029`). The hook
resolves project paths at runtime via `studio/projects.json`.

Session-scoping exists because two Claude Code sessions can share the same working directory
(e.g. one interactive, one headless `--dangerously-skip-permissions` run). Before the fix, both
wrote to the same fixed filename (`.claude/studio-looper.local.md`), and whichever session's Stop
hook fired first "claimed" it via a `session_id: __pending__` race — silently hijacking the queue
from whichever session actually started it. Naming the file after the session that created it
removes the race entirely: each session's hook only ever reads/writes its own file.

A **concurrency guard** (Step 1a) additionally refuses to start a second live run against the
same `target_prefix` even under this scheme — it globs `.claude/studio-looper.*.local.md`,
and if it finds another file targeting the same queue with a still-future deadline, it stops
and reports rather than proceeding. Stale files (deadline passed, task never advanced past
Queue) are auto-cleaned.

**Known limitation:** on an interactive (non-headless) session, creating this file for the first
time each session triggers one unavoidable "Do you want to create X?" confirmation — Claude Code
hard-codes an interactive prompt for any *new* file under a `.claude/` directory regardless of
permission mode or allow-list rules (only `--dangerously-skip-permissions` bypasses it). This is
a one-time-per-session prompt, not a recurring interruption: every subsequent update to the same
file happens via the hook's own shell redirection (not a Claude tool call), so it never re-prompts
mid-loop. For genuinely unattended runs, use `--at` or launch headless directly — see below.

## Test mode

`/studio-looper --test` runs the entire pipeline against a sandbox Asana project (prefix `SLT`,
GID `1216618878942979`) instead of the real `SL` queue, routing to `studio/looper-test/` instead
of `studio/looper/`. Use it to safely test skill/hook changes, headless invocation, or the
concurrency guard without any risk to the real queue or a client repo. Setup is documented in
`studio/looper-test/CLAUDE.md` — it needs a one-time manual step from Mark (adding bainbot as a
member and attaching the shared **Looper Status** field), since Asana project membership changes
require human OAuth, not the bainbot PAT.

## Stop hook

`~/.claude/hooks/studio-task-looper-stop-hook.sh` — fires on every session stop, resolves
*that session's own* state file (`.claude/studio-looper.{firing session's id}.local.md`), reads
it, resolves the next task's project directory, and re-injects the next task prompt into that
same session. Runs alongside the per-project looper hook; each hook only acts on state files
matching its own naming scheme.

## Local ID handling

Tasks multi-homed into Studio Looper keep their original project ID (e.g. MCF-007) via the
workspace-level Local ID custom field. sync.py's `PRESERVE_FOREIGN_IDS: true` flag in
`studio/looper/CLAUDE.md` prevents re-homing them to SL-NNN IDs.

## Setup (one-time)

1. Create "Studio Looper" project in Asana with sections: Queue, In Progress, Blocked, Review, Done
2. Add bainbot as a project member
3. Copy the project GID into `studio/looper/CLAUDE.md` (replace the placeholder)
4. `python3 studio/sync.py --setup --project SL`
5. Multi-home tasks into Queue and run `/studio-looper`

## Per-project looper

`/task-looper BSTD` (the original per-project looper) is unchanged. Use it for targeted
single-project runs. Studio Looper is for cross-project queues curated in Asana.

## Source files

- `studio/looper/CLAUDE.md` — project config (GID, prefix, preserve flag)
- `.claude/skills/studio-looper/SKILL.md` — skill definition
- `~/.claude/hooks/studio-task-looper-stop-hook.sh` — stop hook
- `studio/sync.py` — `preserve_foreign_ids` flag in ProjectConfig

## See also

- [task-looper](../gods/hermes/task-looper.md) — per-project version
- [Hermes](../gods/hermes/) — session orchestration
