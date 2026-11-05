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

1. Mark multi-homes tasks from any project (MCF, NORE, BSTD, UAP…) into the **Studio Looper**
   Asana project, Queue section. Drag order = execution priority.
2. `/studio-looper` syncs the SL project, reads the Queue, and presents the list for
   confirmation before starting.
3. BainBot works each task in the correct project directory (derived from the task's prefix —
   MCF-007 → MCF project path, etc.).
4. On completion: task moves to **Review** section, reassigned to Mark, and gets **one**
   Asana comment — a templated review note opening `@mark`. Task is NOT marked done in Asana.
5. On blocker: task moves to **Blocked** section, reassigned to Mark, with a `@mark Blocked:`
   note carrying the question.
6. Mark reviews tasks in the Review section, marks them done himself.

The note's template, the `@mark` mention that reaches his filtered inbox, and the
one-task-one-comment rule are in [looper-review-comments](looper-review-comments.md).

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

## Documented-answer gate

Before blocking a task on a question, the looper must look for the answer in the task (notes,
comments, linked tasks), the project's CLAUDE.md and ADRs, the studio/dev-root/global CLAUDE.md
files, and the studio ADRs. Standing answers such as "where does research output go" (Dropbox,
never the repo) and "what format" (markdown) are spelled out in the skill. Title-only tasks with
one clearly most likely reading get worked, with what was built named plainly in the review
note's first line so a wrong reading is obvious at a glance. A blocker
that survives must say what was checked and ask one specific question.

Added 2026-09-17 after a run blocked six tasks on questions CLAUDE.md already answered.

## Linked Asana tasks

The looper works from local mirrors, but it is not limited to them. When a task links to another
Asana task, the looper reads it with:

```bash
python3 studio/sync.py --get-task <url|gid|LOCAL-ID>
```

Read-only, via bainbot. Accepts a task URL, a bare GID, or a local ID (resolved through every
registered project's `asana-ids.json`, including paused and archived ones). Prints the task's
local ID, completion state, projects, Looper Status, notes and all comments (bainbot's included).
Exits non-zero with a specific error if the reference can't be resolved or Asana refuses it
(404/403 usually means bainbot isn't a member of that project).

Before this existed (SL-133) the looper blocked every task that pointed at another task.

## State file

`/tmp/studio-looper/studio-looper.{session_id}.local.md` — **session-scoped**, named
from `$CLAUDE_CODE_SESSION_ID` at creation time (Step 3 of the skill). Written by the skill,
read and advanced by the hook. Queue entries are bare task IDs (`MCF-007`, `NORE-029`). The hook
resolves project paths at runtime via `studio/projects.json`.

State moved out of `.claude/` on 2026-07-18: Claude Code hard-prompts on any write to the
project root's `.claude/` directory ("sensitive file"), regardless of allow rules or permission
mode, which broke unattended runs. `/tmp` writes never prompt. Loss of state on reboot is
acceptable — a rebooted machine has no live loop to resume, and the concurrency guard treats a
missing file as no conflict. The hook auto-migrates any old-location state file it finds.

Session-scoping exists because two Claude Code sessions can share the same working directory
(e.g. one interactive, one headless `--dangerously-skip-permissions` run). Before the fix, both
wrote to the same fixed filename (`.claude/studio-looper.local.md`), and whichever session's Stop
hook fired first "claimed" it via a `session_id: __pending__` race — silently hijacking the queue
from whichever session actually started it. Naming the file after the session that created it
removes the race entirely: each session's hook only ever reads/writes its own file.

A **concurrency guard** (Step 1a) additionally refuses to start a second live run against the
same `target_prefix` even under this scheme — it globs `/tmp/studio-looper/studio-looper.*.local.md`,
and if it finds another file targeting the same queue with a still-future deadline AND recent
activity (touched within 15 minutes), it stops and reports rather than proceeding. Stale files
(deadline passed, or 15+ minutes inactive, task never advanced past Queue) are auto-cleaned
without confirmation.

When nothing competes, the guard prints a positive `CLEAR:no other session targets {PREFIX}` line
rather than staying silent, and names the runner (`— launched by runner {id}`) when
`LOOPER_RUN_ID` is set in the environment. Silence turned out to be too weak a signal: on
2026-11-05 a headless iteration read empty output as "the guard is broken", went looking at
processes, found `looper_runner.py` holding `/tmp/studio-looper/runner.lock` along with its own
`claude -p /studio-looper` child, concluded a rival run was already working the queue, and refused
to start. The nightly window ended after 1 of 6 tasks. Nothing was actually wrong — the runner
holds that lock for the whole window by design and had launched the very session that then read it
as a competitor.

Step 1a is therefore explicit that `looper_logic.py concurrency` is the **only** concurrency
signal. A session must not weigh `ps`, `pgrep`, `runner.lock`, or `Session started` lines in
`~/logs/task-looper.log`, because under the runner every one of those shows the session its own
run. The model was left on `haiku` — chosen deliberately on cost in commit `7aef8e1` ("looper runs on
cheapest model with advisor escalation ladder"), and recorded in ADR-009's invocation. Note that
haiku had in fact been told the right thing: Step 1a already said "no output — no conflict, proceed
normally", and it did the opposite. This is being treated as a signal problem first because a
positive `CLEAR` line is cheaper than a nightly model upgrade and the same iteration completed its
code task correctly. If it misjudges again after this change, move the runner to sonnet.

Note where each piece runs from. Cron invokes `looper_runner.py` out of the ops worktree
(`/home/bain/ops/bain-studio`), but `_resolve_studio()` resolves `STUDIO` to the **dev** checkout,
and the runner launches claude with `cwd=STUDIO`. So a nightly session loads dev's `SKILL.md`,
hooks and `settings.local.json`, and Step 1a's absolute path calls dev's `looper_logic.py`. Skill
and guard changes are therefore live on the next nightly run as soon as they're committed to
whatever branch dev has checked out; only `looper_runner.py` itself needs `ops-deploy.sh`. For the
same reason the runner imports `looper_logic` relative to `__file__`, not to `STUDIO` — a
`STUDIO`-relative import would pull the module from whichever branch dev sits on, and on one
without `window_summary` that is an ImportError at module scope, before `notify()` exists, which
would lose the window in silence.

The runner also now distinguishes an early stop from a drained queue. It decides an iteration made
progress by watching `~/logs/task-looper.log` grow, so a session that declines to start looks
exactly like an empty queue. At window end it counts tasks still at Looper Status `Queue` in the SL
mirror; if any remain it logs `ENDED EARLY` and sends a high-priority notification naming them,
instead of reporting a finished window.

The old "one unavoidable prompt per session" limitation is gone: it was caused by the state file
living under `.claude/`, which Claude Code treats as sensitive and always prompts on. With state
in `/tmp` and correctly-written allow rules (`Edit(**)` globs, `//`-prefixed absolute paths),
interactive runs are fully prompt-free.

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
*that session's own* state file (`/tmp/studio-looper/studio-looper.{firing session's id}.local.md`),
reads it, resolves the next task's project directory, and re-injects the next task prompt into
that same session. Runs alongside the per-project looper hook; each hook only acts on state files
matching its own naming scheme.

## Mirror location

`asana-mirror.md` and `asana-ids.json` live at each project's **root**, not `.claude/` — moved
2026-07-22 for the same reason the state file moved to `/tmp`: Claude Code hard-prompts on any
Edit/Write inside `.claude/`, and the looper edits the target mirror on every task it works
(Looper Status, Progress). A mirror under `.claude/` meant at least one blocking prompt per task,
fatal for unattended runs. See [ADR 011](../adr/011-mirrors-at-project-root.md). Symlinks were
left at the old `.claude/asana-mirror.md` / `.claude/asana-ids.json` paths for anything not yet
updated — read/write the root path, never the symlink.

## Evals and tests

Two layers, in `studio/scripts/looper_logic.py`:

- **Unit tests** — `studio/tests/test_looper_logic.py` (pytest, part of the normal suite, free).
  Cover the concurrency guard's LIVE/STALE classification, queue building (Priority sort, `## DONE`
  exclusion), orphan detection, and deadline calculation — logic that used to be duplicated as
  inline Python heredocs inside SKILL.md and was never tested. SKILL.md's Step 1a and Step 2 now
  call this module via CLI (`python3 studio/scripts/looper_logic.py {concurrency|queue|orphans|deadline}`)
  instead of re-embedding the logic, so the doc and the tested code can't drift apart.
- **Behavioral evals** — `studio/evals/studio_looper/run_evals.py`. Invoke the actual skill
  headless against the `SLT` sandbox to check an agent reading SKILL.md really behaves the way it's
  documented to, not just that the extracted functions are correct in isolation. Costs real tokens
  and touches real SLT Asana data — never run automatically, never part of CI. See
  `studio/evals/studio_looper/README.md`.

These evals caught a real bug on first use: `parse_state_frontmatter`'s field regex used `\s*`
between key and value, which matches newlines — on the common case of an empty field followed by
another key (`stop_at_pct:\ntarget_prefix: SL`), it silently swallowed the next line into the
current key's value, corrupting `target_prefix` and making the concurrency guard blind to real
conflicts. Fixed to `[ \t]*` (same line only); covered by a regression test.

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

`/task-looper` is **deprecated** (ADR 009) — its SKILL.md is a redirect stub. For a
targeted single-project run, queue only that project's tasks in Studio Looper.

## Source files

- `studio/looper/CLAUDE.md` — project config (GID, prefix, preserve flag)
- `.claude/skills/studio-looper/SKILL.md` — skill definition
- `~/.claude/hooks/studio-task-looper-stop-hook.sh` — stop hook
- `studio/sync.py` — `preserve_foreign_ids` flag in ProjectConfig

## See also

- [task-looper](../gods/hermes/task-looper.md) — per-project predecessor, deprecated (ADR 009)
- [Hermes](../gods/hermes/) — session orchestration
