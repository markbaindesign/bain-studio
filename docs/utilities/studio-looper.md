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
/studio-looper                    # start a window now (launches the runner)
/studio-looper --for 2h           # start no new task after 2 hours
/studio-looper --use 10%          # stop once 10 more points of the 5-hour quota are used
/studio-looper --at 20:00         # the runner sleeps until 20:00, then runs a window
/studio-looper --dry-run          # show the queue, launch nothing
/studio-looper --health-check     # verify the chain, touch nothing
/studio-looper --test             # the sandbox SLT queue instead of SL
```

The skill is a trigger: it checks for a competing run, shows the queue and launches
`studio/scripts/looper_runner.py` in the background. The runner does the work, and is what cron
runs nightly:

```bash
python3 studio/scripts/looper_runner.py --now [--target SLT] [--until ISO] [--stop-at-pct N]
python3 studio/scripts/looper_runner.py --at 02:00
```

Must be invoked from `/media/data/dev/bain-studio`.

## Scheduled windows

Cron runs the queue headless through `studio/scripts/looper_runner.py`, from the ops worktree:

| Window | Cron | Length |
|---|---|---|
| Nightly | `0 2 * * *` `looper_runner.py --now` | until the queue drains or the quota window ends |
| Lunch hour | `0 15 * * 1-5` `looper_runner.py --now --minutes 60` | one hour, weekdays, while Mark is away from the keyboard |

`--minutes N` stops the runner starting a new task N minutes after the window opens. A task
already running finishes rather than being killed halfway, so a window can overrun by one
task. Both windows run on the Max login (`max_plan_env`), never the API key.

## How it works

1. Mark multi-homes tasks from any project (MCF, NORE, BSTD, UAP…) into the **Studio Looper**
   Asana project. From a session:
   `python3 studio/sync.py --add-to-project SL --task-gid BSTD-893,BSTD-894`.
2. The runner syncs SL, resets any task stranded at In Progress, and takes the top task of the
   queue (Priority, then mirror order).
3. It resolves the task's home project from its prefix through the registry, makes a git
   worktree for it outside the project, and starts a **confined** `claude -p` session there
   (below). The session does the work, commits once on the task's branch, and posts **one**
   `@mark` note — `Review:` or `Blocked:` — through `sync.py --comment`.
4. The runner moves Looper Status to **Review** or **Blocked** and reassigns to Mark. The task is
   never marked done in Asana.
5. Next task, until the queue is empty, the deadline or usage cap is reached, or a session stops
   at the Max usage limit.
6. Mark reviews tasks in Review and marks them done himself.

The note's template, the `@mark` mention that reaches his filtered inbox, and the
one-task-one-comment rule are in [asana-comments](asana-comments.md).

## Worktrees and confinement

Since BSTD-893 every task runs in a worktree of its own and the project's checkout is never
switched or written to. Before, the session switched the project's own checkout to the looper
branch and back: Mark's uncommitted work rode along, overlap was caught only by an instruction,
a failed switch-back left the folder on the looper branch, and the session ran with
`--dangerously-skip-permissions`.

| | |
|---|---|
| Worktree | `~/.local/share/bain-bot-worktrees/{PREFIX}/looper-{run}-{TASK}` |
| Branch | `looper/{run}/{TASK}` from `develop` (else `main`). One per task: git checks a branch out in one worktree only. |
| Session | `bot_worktree.confined_argv`, shared with the webhook runs (ADR 025): `--restricted`, `Edit` only inside the worktree and denied in the checkout, git limited to status/diff/log/show/add/commit, `sync.py --get-task`/`--comment`, no network, no outward tools, credential files unreadable |
| Read-only | the studio's `docs/` (ADRs), the registry, the project's `DROPBOX_FOLDER` |
| Sandbox | SLT tasks work in `studio/looper-test/` inside a worktree of the studio repo; SL-native tasks have no repo and are blocked |
| Account | the project's `.envrc` `CLAUDE_CONFIG_DIR`, so a client on its own Claude account is billed there (ADR 017) |
| No commits | worktree and branch removed |
| Commits | kept for review; in a repo with the commit guard installed, checked against the client-data denylist (runs commit with hooks off); a hit notifies at high priority |
| No result | the runner blocks the task with its own note naming the run log |

A confined session cannot write a report into Dropbox, or run tests and builds (BSTD-896). Both
come back as a `Blocked:` or a `Gaps:` line rather than a failure.

A repo that already has a `looper/{run}` branch from an older run cannot also hold
`looper/{run}/{TASK}` (git refs are paths). Run ids are minute stamps, so this only bites a
re-run within the same minute as an old-style run.

The task prompt is `TASK_PROMPT` in `looper_runner.py`. It carries what used to be the skill's
Step 4: the duplicate-work guard, the documented-answer gate, the note format.

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

> The runner writes no state file and never launches this skill. What follows describes the
> interactive concurrency guard, which still reads state files left by older builds; the runner's
> per-queue lock (`/tmp/studio-looper/runner.lock`, `runner-SLT.lock`) is the live signal.

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
normally", and it did the opposite. (Moved to Opus on 2026-11-18, once runs billed to the Max
plan rather than API credits; see ADR 009.) This is being treated as a signal problem first because a
positive `CLEAR` line is cheaper than a nightly model upgrade and the same iteration completed its
code task correctly. If it misjudges again after this change, move the runner to sonnet.

Note where each piece runs from. Cron invokes `looper_runner.py` out of the ops worktree
(`/home/bain/ops/bain-studio`), but `_resolve_studio()` resolves `STUDIO` to the **dev** checkout:
the mirrors and `sync.py` it drives live there. The runner imports `looper_logic` and
`bot_worktree` relative to `__file__`, so its code, the task prompt and the confinement rules all
come from the ops deploy and change only with `ops-deploy.sh`.

The runner also distinguishes an early stop from a drained queue. At window end it counts tasks still at Looper Status `Queue` in the SL
mirror; if any remain it logs `ENDED EARLY` and sends a high-priority notification naming them,
instead of reporting a finished window.

The old "one unavoidable prompt per session" limitation is gone: it was caused by the state file
living under `.claude/`, which Claude Code treats as sensitive and always prompts on. With state
in `/tmp` and correctly-written allow rules (`Edit(**)` globs, `//`-prefixed absolute paths),
interactive runs are fully prompt-free.

## Test mode

`/studio-looper --test` runs the entire pipeline against a sandbox Asana project (prefix `SLT`)
instead of the real `SL` queue, routing to `studio/looper-test/` instead
of `studio/looper/`. Use it to safely test skill/hook changes, headless invocation, or the
concurrency guard without any risk to the real queue or a client repo. Setup is documented in
`studio/looper-test/CLAUDE.md` — it needs a one-time manual step from Mark (adding bainbot as a
member and attaching the shared **Looper Status** field), since Asana project membership changes
require human OAuth, not the bainbot PAT.

## Stop hook

`~/.claude/hooks/studio-task-looper-stop-hook.sh` re-injected the next task into an interactive
session from its state file. Nothing writes one any more, so it no longer fires for the looper.

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
- `.claude/skills/studio-looper/SKILL.md` — skill definition (a trigger for the runner)
- `studio/scripts/looper_runner.py` — the runner: queue, worktree, confined session, status
- `studio/bot_worktree.py` — worktrees and the confined command line, shared with the webhook
- `studio/scripts/looper_logic.py` — queue, mirror edits, outcome parsing (unit-tested)
- `studio/tests/test_looper_runner.py` — temp-repo tests with a fake `claude`
- `studio/sync.py` — `preserve_foreign_ids` flag in ProjectConfig

## See also

- [task-looper](../gods/hermes/task-looper.md) — per-project predecessor, deprecated (ADR 009)
- [Hermes](../gods/hermes/) — session orchestration
