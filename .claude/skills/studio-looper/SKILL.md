---
name: studio-looper
description: "Cross-project task queue: works BainBot tasks from any studio project in Asana priority order, handing finished work to Mark for review."
allowed-tools: [Bash, Read, Edit]
---

# Studio Looper

Works tasks multi-homed into the Studio Looper Asana project. The queue is every task whose
**Looper Status** custom field reads "Queue". Never marks tasks done — moves them to "Review" for Mark.

**This skill is a trigger for `studio/scripts/looper_runner.py`, which does the work.** For each
task the runner makes a git worktree of its own, outside the project, on branch
`looper/{run}/{TASK}`, and starts a confined `claude -p` session in it: `--restricted`, edits only
inside the worktree, no network, no outward tools, never `--dangerously-skip-permissions`. The
project's own checkout is never switched or written to, so Mark's uncommitted work there cannot
reach a looper commit. The runner moves Looper Status, removes a worktree that committed nothing,
and checks a kept branch against the client-data denylist. See ADR 009 and
`docs/utilities/studio-looper.md`.

This session never works a task itself. It checks, shows the queue, launches the runner, and stops.

Must be invoked from `/media/data/dev/bain-studio`.

## Usage

```
/studio-looper                    — start the queue
/studio-looper --for 2h           — run for up to 2 hours
/studio-looper --use 10%          — consume at most 10% of quota
/studio-looper --yes              — accepted for compatibility; never asks anyway
/studio-looper --at 20:00         — schedule queue run at 20:00 today
/studio-looper --dry-run          — show queue without working any tasks
/studio-looper --health-check      — verify setup end-to-end, touch nothing, report and exit
/studio-looper --test             — run against the sandbox test queue (SLT) instead of SL
```

Flags can be combined: `/studio-looper --at 20:00 --for 2h`, `/studio-looper --test --yes`

---

## Step 0 — Parse flags

Parse all flags before doing anything:

**`--test`**:
Set `TARGET_PREFIX=SLT` and `TARGET_DIR=studio/looper-test`. Otherwise `TARGET_PREFIX=SL` and
`TARGET_DIR=studio/looper` (the defaults). Every step below that references "the target project",
`{TARGET_PREFIX}`, or `{TARGET_DIR}` uses whichever pair was resolved here. Test-mode runs are
tagged `[SLT]` (not `[SL]`) in every log line and notification, so they're never mistaken for a
real run in `~/logs/task-looper.log` or Slack.

**`--for DURATION`** (e.g. `--for 1h`, `--for 30m`, `--for 1h30m`):
Calculate `(now + duration).isoformat(timespec="minutes")` → store as `FOR_DEADLINE`. Passed to
the runner as `--until {FOR_DEADLINE}`: it starts no new task after that time.

**`--use N%`**:
Read current usage from `~/.claude/ratelimit-current.json`. Calculate stop threshold:
`stop_at = min(100, current_pct + N)` → store as `STOP_AT_PCT`. Passed to the runner as
`--stop-at-pct {STOP_AT_PCT}`: it checks usage before each task.

**`--at TIME`** (e.g. `--at 20:00`):
The runner schedules itself. Run Step 1 and Step 1a first, then launch it with the other flags
translated (`RUNNER_FLAGS`: `--target SLT` for `--test`, `--until`, `--stop-at-pct`):
```bash
nohup python3 studio/scripts/looper_runner.py --at {TIME} {RUNNER_FLAGS} >> ~/logs/studio-looper-cron.log 2>&1 &
disown $!
```
Confirm: "Scheduled the looper runner for {TIME}." Then **stop**.

**`--dry-run`**:
Set `DRY_RUN=true`. Steps 1 and 2 run normally (sync + build queue). Print the queue and stop — do not launch the runner.

**`--health-check`**:
Set `HEALTH_CHECK_MODE=true`. Runs the full pipeline through queue-build and validation (Steps 1, 1a, 1c, 2, 2b),
logs and Slack-notifies the result, then stops. Does not change any Looper Status, launch the
runner, or work any task — see Step 2b. Purpose: confirm the whole chain (sync, mirror parsing,
project-prefix resolution, notifier) is healthy before trusting an unattended `--for`/`--at` run.

**`--yes`**:
Accepted for compatibility. The skill never asks for confirmation.

---

## Step 1 — Confirm CWD

```bash
pwd
```

Must be `/media/data/dev/bain-studio` (a symlink to it, e.g. `/home/bain/code/bain-studio`, is fine
— resolve with `pwd -P` if unsure). If neither, stop: "studio-looper must be run from the studio root."

---

## Step 1a — Concurrency guard

Before touching anything, check whether another session is already actively driving the **same**
target queue. This is what prevents the exact collision that motivated session-scoping in the
first place: an interactive session and a headless session both racing on `SL`.

```bash
python3 /media/data/dev/bain-studio/studio/scripts/looper_logic.py concurrency {TARGET_PREFIX}
```

(This calls the same `classify_concurrency` function covered by
`studio/tests/test_looper_logic.py` — logic lives there, not inline, so it's unit-tested
rather than re-derived by each session.)

For each line printed:

- **`LIVE:...`** — another session is actively working this exact target queue: its deadline
  hasn't passed AND its state file has been touched within the last 15 minutes. **Stop the run.**
  Tell Mark: "studio-looper [{TARGET_PREFIX}] is already running in session {session}, currently
  on {current_task} (deadline {deadline}). Not starting a second run against the same queue — use
  `--test` to test safely, or wait for it to finish." Do not delete the other session's file.
- **`STALE:...`** — either the deadline has passed, or the state file hasn't been touched in 15+
  minutes (the reason is tagged on the line: `deadline` or `inactive-{N}m`). Both mean the same
  thing operationally: no live session is actually advancing this queue anymore — crashed, killed,
  or the interactive session behind it was ended by Mark without the loop reaching a promise. This
  is now the **default, automatic path** — no need to ask Mark before clearing it. Before clearing,
  do one safety check: read `current_task`'s Looper Status in the target mirror.
  - If it's already past `Queue` (e.g. `In Progress`), something may still be mid-flight in a way
    the mirror hasn't caught up with — stop and tell Mark rather than clearing.
  - If it's still `Queue` (never advanced), the old session did nothing useful — clear it and
    continue automatically, no confirmation needed:
    ```bash
    rm -f {path}
    echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [{TARGET_PREFIX}] Removed stale state file ({path}, deadline {deadline_s}, session_id {session}, reason {reason_tag}) — {current_task} still Queue, restarting queue fresh" >> ~/logs/task-looper.log
    ```
  Then continue straight to Step 1b — do not stop the run over a stale file, and do not wait for
  further input.
- **`CLEAR:...`** — no other session targets this queue. Go on to the runner-lock check below.
- **No output at all** — an older build of `looper_logic.py` with no `CLEAR` line. Same meaning.

**Then check the runner's lock.** The runner holds a lock for the whole window and writes no state
file, so the script above cannot see it:

```bash
LOCK=/tmp/studio-looper/runner.lock          # SL
[ "{TARGET_PREFIX}" = SLT ] && LOCK=/tmp/studio-looper/runner-SLT.lock
[ -f "$LOCK" ] && kill -0 "$(cat "$LOCK")" 2>/dev/null && echo "RUNNING:$(cat "$LOCK")"
```

`RUNNING:{pid}` means a window is in progress on this queue. Do not start, and do not touch its
mirror: tell Mark "a looper window is already running on {TARGET_PREFIX} (runner pid {pid})" and
stop. The runner would refuse a second lock anyway; stopping here keeps this session's sync and
queue display from racing the runner's own mirror edits.

The skill never runs inside a runner window any more (the runner works each task in its own
confined session), so a lock or a `looper_runner.py` process is never this session's own.

---

## Step 1b — Sync target project

Full-project syncs regularly exceed the default 120s command timeout (the SL project fetches
~100 tasks with comments). **Always pass an explicit long timeout** so the sync completes in the
foreground:

```bash
# Bash tool call MUST set timeout: 600000 — never let this get auto-backgrounded
python3 studio/sync.py --project {TARGET_PREFIX}
```

**Never end your turn while a sync is in flight.** In a headless (`-p`) session, ending the turn
kills the process — a backgrounded sync's completion notification has no session left to wake,
and the whole run dies silently (this exact failure ate the 2026-07-18 20:00 scheduled window).
If a sync does get backgrounded anyway, block on it in the foreground:
```bash
until [ -n "$(tail -c 100 {OUTPUT_FILE} 2>/dev/null | grep 'Done')" ]; do sleep 5; done
```

If the sync fails because the {TARGET_PREFIX} project GID is not configured, stop and tell Mark
to complete the setup in `{TARGET_DIR}/CLAUDE.md`.

---

## Step 1c — Check usage headroom

```bash
python3 - <<'PYEOF'
import json, datetime
from pathlib import Path

rl = Path.home() / ".claude/ratelimit-current.json"
pct, reset_str = "?", "unknown"
if rl.exists():
    data = json.loads(rl.read_text())
    pct = data.get("current_pct", "?")
    reset_ts = data.get("reset_ts")
    reset_str = datetime.datetime.fromtimestamp(reset_ts).strftime("%Y-%m-%d %H:%M") if reset_ts else "unknown"

print(f"usage:{pct}:{reset_str}")
PYEOF
```

Log and continue. The `--use` cap is enforced by the runner, which reads usage before each task.

---

## Step 2 — Build queue from target mirror

Orphan recovery (tasks stranded at `In progress` by a run that died) is the runner's job: it holds
the lock for the queue, so at the start of each window anything still `In progress` is an orphan
and goes back to `Queue`. This session does not reset anything.

Build the queue — tasks with `**Looper Status:** Queue` that sit above the mirror's `## DONE`
section, sorted by Priority (High > Medium > Low > none) then mirror order as tiebreak:
```bash
python3 studio/scripts/looper_logic.py queue {TARGET_DIR}/asana-mirror.md
```
Each line is `{local_id}\t{priority}\t{title}`, already in the order to work them.

**Never queue a completed task.** Tasks in `## DONE` are finished in Asana regardless of what
their Looper Status field reads — a stale "Queue" on a completed task is field noise, not work.
(sync.py also annotates these as `Queue (completed, not workable)` so the exact match fails, but
the section filter — enforced by `looper_logic.build_queue`, see
`studio/tests/test_looper_logic.py` — is the rule even if the annotation is ever missing.)

If queue is empty: notify and stop.

**If `--health-check`: run Step 2b instead. Do not proceed to Step 3.**

**Never ask for confirmation.** Print the queue as a one-off status line and proceed straight to
Step 3 — the looper's entire purpose is unattended running, and stopping to ask defeats it:
```
Studio Looper [{TARGET_PREFIX}] — {N} tasks queued: MCF-007, NORE-029, BSTD-021. Launching the runner.
```
(The old `--yes` flag is accepted for backwards compatibility but is now the default and only
behaviour. To exclude tasks from a run, change their Looper Status in Asana before invoking.)

---

## Step 2b — Health check mode (`--health-check` only)

Verify the whole chain is healthy without touching any state — no Looper Status change, no state
file, no work done. Check each of the following and collect PASS/FAIL:

1. **Sync** — Step 1b already ran; PASS if it exited 0.
2. **Queue parse** — PASS if Step 2 produced a queue (empty queue is a FAIL for `--health-check`, since an
   empty queue on a day with known tasks usually means a parsing problem, not truly no work).
3. **Project resolution** — for every distinct prefix in the queue (not every task, just distinct
   prefixes), run the runner's lookup: `python3 studio/registry.py --prefix {PREFIX} --field path`,
   and check that path is the top of its own git repository (`git -C {path} rev-parse
   --show-toplevel`). FAIL any prefix that does not resolve or has no repository, and name it.
4. **Mirror presence** — for each resolved project dir, confirm `asana-mirror.md` and
   `CLAUDE.md` exist. FAIL any that are missing.
5. **Log writable** — confirm `~/logs/task-looper.log` can be appended to.
6. **Notifier reachable** — this is exercised by the notify call below; if `notifier.py` exits
   non-zero, that's a FAIL for this check.

Log the result:
```bash
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [{TARGET_PREFIX}] --health-check run: {PASS_COUNT}/{CHECK_COUNT} checks passed — {N} tasks queued. {FAIL_SUMMARY or 'all clear'}" >> ~/logs/task-looper.log
```

Notify Slack with the same summary:
```bash
python3 studio/notifier.py \
  "studio-looper --health-check [{TARGET_PREFIX}]: {PASS_COUNT}/{CHECK_COUNT} checks passed — {N} tasks queued. {FAIL_SUMMARY or 'all clear'}" \
  --priority {normal if all passed else high} --sender studio-task-looper --project {TARGET_PREFIX} --channel looper
```

Report the same summary to Mark in chat, then **stop**. Do not write any state file, do not change
any Looper Status, do not sync anything else, do not proceed to Step 3.

---

## Step 3 — Launch the runner

Translate the flags into `RUNNER_FLAGS`: `--target SLT` for `--test`, `--until {FOR_DEADLINE}` for
`--for`, `--stop-at-pct {STOP_AT_PCT}` for `--use`. Then start it in the background, so a window of
several hours does not depend on this session staying open:

```bash
mkdir -p ~/logs
nohup python3 studio/scripts/looper_runner.py --now {RUNNER_FLAGS} >> ~/logs/studio-looper-cron.log 2>&1 &
echo "runner pid $!"; disown $!
```

Log and report, then **stop**. Do not wait for it, and do not work any task in this session:

```bash
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [{TARGET_PREFIX}] Runner launched interactively ({PARAMS}) — {N} tasks queued: {IDs}" >> ~/logs/task-looper.log
```

Tell Mark: "Looper runner started on {TARGET_PREFIX} (pid {pid}), {N} tasks queued. Progress in
`~/logs/studio-looper.log`; each task's session in `~/logs/studio-looper-run-*.log`."

---

## What the runner does for each task

Reference only: this is `looper_runner.work_task`, not instructions for this session.

1. Re-reads the queue mirror and takes the top task (Priority, then mirror order). A task already
   worked this window is not taken again.
2. Sets Looper Status to `In Progress` (mirror edit + sync, confirmed by sync.py's `Pushed to`).
3. Resolves the home project from the task's prefix **through the registry only**. No registered
   repository (an SL-native task, an unregistered project) → Blocked with its own note.
4. Makes a worktree at `~/.local/share/bain-bot-worktrees/{PREFIX}/looper-{run}-{TASK}` on branch
   `looper/{run}/{TASK}`, from `develop` (or `main`). One branch per task: git checks a branch out
   in one worktree only, and the tidy step counts the branch's own commits.
5. Starts `claude -p` in the worktree with the task prompt (`TASK_PROMPT` in the runner) and
   `bot_worktree.confined_argv`: `--restricted`, `Edit` allowed only in the worktree and denied in
   the project checkout, git limited to status/diff/log/show/add/commit, `sync.py --get-task` and
   `--comment` the only other commands, no network, no outward tools, credential files unreadable,
   the studio's `docs/`, the registry and the project's Dropbox folder readable but not writable. The
   project's `.envrc` `CLAUDE_CONFIG_DIR` is honoured, so a client on its own Claude account is
   billed there. The session reads the task, does the work, commits once, posts **one** `@mark`
   `Review:` or `Blocked:` note through `sync.py --comment`, and ends with
   `<promise>{TASK}_COMPLETE</promise>` or `<promise>{TASK}_BLOCKED</promise>`.
6. Tidies the worktree: nothing committed or changed → worktree and branch removed. Commits → kept
   for Mark, and checked against the client-data denylist in a repo with the commit guard
   installed (runs commit with hooks off); a hit is a high-priority notification.
7. Sets Looper Status to `Review` or `Blocked` and hands the task to Mark. No promise at all →
   Blocked, with the runner's own note pointing at the run log. A session stopped by the Max usage
   limit → back to `Queue`, and the window ends.

Task events go to `~/logs/task-looper.log`, window events to `~/logs/studio-looper.log`.

---

## Guard rails

- Never mark a task DONE in Asana — the runner moves it to Review and reassigns to Mark.
  Completing it is Mark's approval, and it is his click.
- **This session never works a task.** Working a task in an unconfined interactive session is
  exactly what the runner exists to prevent: the project checkout switched under Mark, his WIP in
  a looper commit, a failed switch-back leaving the folder on a looper branch.
- **One Asana task gets one comment**, posted by the task's own session. Nothing writes a
  Progress note into either mirror for a looper task.
- **`@mark` is the only thing Mark sees** (his inbox is filtered to *Mentioned*). Review and
  blocked notes only.
- Looper branches are never pushed or merged. Review and merge are Mark's.
- Never start a second run against the same `{TARGET_PREFIX}`: Step 1a's guard and the runner's
  own lock both refuse. Use `--test` to try changes to the looper safely.
- **Never run two sync.py invocations for the same project concurrently.** sync.py reads the mirror
  at start and rewrites it at the end, so overlapping runs race and the loser silently reverts
  Looper Status edits. While a window runs, the runner is the only thing that syncs the queue.
