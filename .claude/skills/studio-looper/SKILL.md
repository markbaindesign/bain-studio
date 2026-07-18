---
name: studio-looper
description: Cross-project task queue — works BainBot tasks from any studio project in Asana priority order. Advances tasks through Looper Status field. Hands completed work to Mark for review rather than marking done.
allowed-tools: [Bash, Read, Edit]
---

# Studio Looper

Works tasks multi-homed into the Studio Looper Asana project. BainBot reads the **Looper Status**
custom field to build the queue (all tasks with status "Queue"), works each in project-dir context,
and advances the status through the field. Never marks tasks done — moves to "Review" for Mark.

Must be invoked from `/media/data/dev/bain-studio`.

State files are **session-scoped**: `.claude/studio-looper.{session_id}.local.md`, named at
creation time from `$CLAUDE_CODE_SESSION_ID`. This lets an interactive session and a headless
session share the same working directory without one session's Stop hook hijacking the other's
queue — each session's hook only ever touches the file matching its own session_id. A
**concurrency guard** (Step 1a) additionally refuses to start a second live run against the same
target queue, even under different sessions.

## Usage

```
/studio-looper                    — start the queue
/studio-looper --for 2h           — run for up to 2 hours
/studio-looper --use 10%          — consume at most 10% of quota
/studio-looper --yes              — skip queue confirmation
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
Calculate deadline: `(now + duration).isoformat()` → store as `FOR_DEADLINE`.

**`--use N%`**:
Read current usage from `~/.claude/ratelimit-current.json`. Calculate stop threshold:
`stop_at = min(100, current_pct + N)` → store as `STOP_AT_PCT`.

**`--at TIME`** (e.g. `--at 20:00`):
Schedule the looper to run at the given time today. Preserve any other flags (e.g. `--test`,
`--for`) in the scheduled invocation. Try `at` first, fall back to Python sleep:
```bash
if command -v at &>/dev/null; then
    echo "cd /media/data/dev/bain-studio && claude --dangerously-skip-permissions -p '/studio-looper --yes{EXTRA_FLAGS}'" | at {TIME}
else
    python3 - <<'PYEOF'
import time, subprocess, sys, datetime
hh, mm = map(int, sys.argv[1].split(":"))
target = datetime.datetime.now().replace(hour=hh, minute=mm, second=0, microsecond=0)
delay = (target - datetime.datetime.now()).total_seconds()
if delay <= 0:
    print(f"ERROR: {sys.argv[1]} is in the past."); sys.exit(1)
open("/tmp/studio-looper-scheduled.py","w").write(
    f"import time,subprocess\ntime.sleep({delay})\nsubprocess.run(['claude','--dangerously-skip-permissions','-p','/studio-looper --yes{EXTRA_FLAGS}'],cwd='/media/data/dev/bain-studio')")
PYEOF
    python3 - {TIME}
    nohup python3 /tmp/studio-looper-scheduled.py >> ~/logs/studio-looper.log 2>&1 &
    disown $!
fi
```
Confirm: "Scheduled /studio-looper for {TIME}." Then **stop** — do not proceed to Step 1.

**`--dry-run`**:
Set `DRY_RUN=true`. Steps 1 and 2 run normally (sync + build queue). Print the queue and stop — do not work any tasks, do not write the state file.

**`--health-check`**:
Set `HEALTH_CHECK_MODE=true`. Runs the full pipeline through queue-build and validation (Steps 1, 1a, 1c, 2, 2b),
logs and Slack-notifies the result, then stops. Does not skip confirmation, write state, change any
Looper Status, or work any task — see Step 2b. Purpose: confirm the whole chain (sync, mirror parsing,
project-prefix resolution, notifier) is healthy before trusting an unattended `--for`/`--at` run.

**`--yes`**:
Skip the queue confirmation prompt in Step 2.

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
python3 - <<'PYEOF'
import datetime, glob, re
from pathlib import Path

target_prefix = "{TARGET_PREFIX}"
now = datetime.datetime.now()

for path in glob.glob(".claude/studio-looper.*.local.md"):
    text = Path(path).read_text()
    fm = text.split("---")[1] if text.count("---") >= 2 else ""
    def field(name):
        m = re.search(rf"^{name}:\s*(.*)$", fm, re.MULTILINE)
        return m.group(1).strip() if m else ""

    file_target = field("target_prefix") or "SL"
    deadline_s = field("deadline")
    session = field("session_id")
    current_task = field("current_task")

    if file_target != target_prefix:
        continue  # different queue entirely — no conflict, ignore

    deadline = None
    if deadline_s:
        try: deadline = datetime.datetime.fromisoformat(deadline_s)
        except ValueError: pass

    if deadline and now >= deadline:
        print(f"STALE:{path}:{deadline_s}:{session}:{current_task}")
    else:
        print(f"LIVE:{path}:{deadline_s}:{session}:{current_task}")
PYEOF
```

For each line printed:

- **`LIVE:...`** — another session is actively working this exact target queue and its deadline
  hasn't passed. **Stop the run.** Tell Mark: "studio-looper [{TARGET_PREFIX}] is already running
  in session {session}, currently on {current_task} (deadline {deadline}). Not starting a second
  run against the same queue — use `--test` to test safely, or wait for it to finish." Do not
  delete the other session's file.
- **`STALE:...`** — the deadline has passed; this is a crashed/killed/orphaned session, not live
  work. Confirm it's genuinely orphaned before clearing: check `current_task`'s Looper Status in
  the target mirror. If it's already past `Queue` (e.g. `In Progress`), something may still be
  mid-flight — stop and tell Mark rather than clearing. If it's still `Queue` (never advanced),
  the old session did nothing useful:
  ```bash
  rm -f {path}
  echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [{TARGET_PREFIX}] Removed stale state file ({path}, deadline {deadline_s}, session_id {session}) — orphaned session, {current_task} still Queue" >> ~/logs/task-looper.log
  ```
  Then continue — do not stop the run over a stale file.
- **No output at all** — no conflict, proceed normally.

---

## Step 1b — Sync target project

```bash
python3 studio/sync.py --project {TARGET_PREFIX}
```

If this fails because the {TARGET_PREFIX} project GID is not configured, stop and tell Mark to
complete the setup in `{TARGET_DIR}/CLAUDE.md`.

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

Log and continue. (The old `stop_at_pct` quota-spent check happens per-iteration inside the
running loop via Step 4e's usage read — this step is just a sanity log at start.)

If re-entering this step from the stop hook re-injection (mid-loop, not a fresh invocation), also
re-check `stop_at_pct` against current usage from the state file named in the injected prompt; if
spent, log `QUOTA_SPENT`, notify, and stop without outputting a promise (the loop simply ends).

---

## Step 2 — Build queue from target mirror

Read `{TARGET_DIR}/.claude/asana-mirror.md`. Extract all tasks where:
- `**Looper Status:** Queue`

Sort the queue by Priority, then mirror order as tiebreaker:
1. High priority
2. Medium priority
3. Low priority
4. No priority set

Calculate deadline — earlier of quota reset or `--for` duration:
```bash
python3 - <<'PYEOF'
import json, datetime
from pathlib import Path

reset_deadline = None
rl = Path.home() / ".claude/ratelimit-current.json"
if rl.exists():
    data = json.loads(rl.read_text())
    ts = data.get("reset_ts")
    if ts:
        reset_deadline = datetime.datetime.fromtimestamp(ts)

for_deadline = None
for_str = "{FOR_DEADLINE}"
if for_str and for_str != "{FOR_DEADLINE}":
    try: for_deadline = datetime.datetime.fromisoformat(for_str)
    except ValueError: pass

candidates = [d for d in [reset_deadline, for_deadline] if d]
if candidates:
    print(min(candidates).isoformat())
PYEOF
```

If queue is empty: notify and stop.

**If `--health-check`: skip the confirmation prompt below and run Step 2b instead. Do not proceed to Step 3.**

Present the queue for confirmation (unless `--yes` or `--health-check`):
```
Studio Looper [{TARGET_PREFIX}] — {N} tasks queued:

  1. MCF-007  [High] — Add blog category filter          (MCF)
  2. NORE-029 [High] — Fix broken contact form           (NORE)
  3. BSTD-021 [Low]  — Add API cost tracker              (BSTD)

Proceed? Press Enter to confirm, or list IDs to skip (e.g. "NORE-029 BSTD-021"):
```

---

## Step 2b — Health check mode (`--health-check` only)

Verify the whole chain is healthy without touching any state — no Looper Status change, no state
file, no work done. Check each of the following and collect PASS/FAIL:

1. **Sync** — Step 1b already ran; PASS if it exited 0.
2. **Queue parse** — PASS if Step 2 produced a queue (empty queue is a FAIL for `--health-check`, since an
   empty queue on a day with known tasks usually means a parsing problem, not truly no work).
3. **Project resolution** — for every distinct prefix in the queue (not every task, just distinct
   prefixes), run the same lookup as Step 4a against `studio/projects.json`. FAIL any prefix that
   resolves to `NOT_FOUND`, and name it.
4. **Mirror presence** — for each resolved project dir, confirm `.claude/asana-mirror.md` and
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
any Looper Status, do not sync anything else, do not proceed to Step 3 or Step 4.

---

## Step 3 — Write state file

Get this session's own ID from the `CLAUDE_CODE_SESSION_ID` environment variable — do not invent
one, and do not use `__pending__`. Write it to
`.claude/studio-looper.{CLAUDE_CODE_SESSION_ID}.local.md`. First task in `current_task`, rest in body:

```
---
session_id: {CLAUDE_CODE_SESSION_ID}
current_task: {FIRST_TASK_ID}
iteration: 0
max_iterations: 30
deadline: {DEADLINE_ISO}
stop_at_pct: {STOP_AT_PCT}
target_prefix: {TARGET_PREFIX}
---
{SECOND_TASK_ID}
{THIRD_TASK_ID}
...
```

In the target mirror, set `current_task`'s **Looper Status** to `In Progress`, then sync:
```bash
# Edit {TARGET_DIR}/.claude/asana-mirror.md: change Looper Status from Queue → In Progress
python3 studio/sync.py --project {TARGET_PREFIX}
```

Build a `{PARAMS}` string from whichever flags were passed in Step 0 (omit any that weren't set),
e.g. `--for 5m`, `--use 10%`, `--test`, `--for 1h --use 10%`. If no flags were passed, `{PARAMS}` is `no limit set`.

Notify and log session start:
```bash
python3 studio/notifier.py \
  "studio-looper [{TARGET_PREFIX}] starting ({PARAMS}) — {N} tasks queued" \
  --priority normal --sender studio-task-looper --project {TARGET_PREFIX} --channel looper
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [{TARGET_PREFIX}] Session started ({PARAMS}) — session {CLAUDE_CODE_SESSION_ID} — {N} tasks: {IDs}" >> ~/logs/task-looper.log
```

---

## Step 4 — Work the first task

### 4a. Navigate to the task's project

```bash
python3 - <<'PYEOF'
import json, os, sys
prefix = sys.argv[1].split('-')[0]
projects = json.load(open('/media/data/dev/bain-studio/studio/projects.json'))
for p in projects:
    cm = os.path.join(p['path'], 'CLAUDE.md')
    if os.path.exists(cm) and f'ASANA_TASK_PREFIX: {prefix}' in open(cm).read():
        print(p['path']); sys.exit(0)
print('NOT_FOUND')
PYEOF
python3 - {CURRENT_TASK}
```

If `NOT_FOUND`: mark blocked ("prefix not found in projects.json") and output blocked promise.

```bash
cd {PROJECT_DIR}
```

### 4b. Read the task

Read `{PROJECT_DIR}/.claude/asana-mirror.md` for task Notes, Blockers, Dependencies.
Read `{PROJECT_DIR}/CLAUDE.md` for the project's tech stack and build instructions.

### 4c. Work

Do the work. One commit when done:
```bash
git add <specific files>
git commit -m "..."
git push origin develop
```

### 4d. Assess completion

**Complete**: problem solved, change works, nothing newly broken.
**Blocked**: needs Mark input, ambiguous, external dependency missing.

### 4e — If complete (REVIEW workflow)

Read current usage:
```bash
python3 - <<'PYEOF'
import json, datetime
from pathlib import Path
rl = Path.home() / ".claude/ratelimit-current.json"
pct, reset_dt = "?", "unknown"
if rl.exists():
    data = json.loads(rl.read_text())
    pct = data.get("current_pct", "?")
    reset_ts = data.get("reset_ts")
    reset_dt = datetime.datetime.fromtimestamp(reset_ts).strftime("%Y-%m-%d %H:%M") if reset_ts else "unknown"
log = Path.home() / "logs/task-looper.log"
ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
log.open("a").write(f"{ts} INFO    [{TARGET_PREFIX}] usage-end: {pct}% — resets {reset_dt}\n")
print(f"usage:{pct}:{reset_dt}")
PYEOF
```

**1. Update target mirror** (`{TARGET_DIR}/.claude/asana-mirror.md`):
```
**Looper Status:** Review
**Assignee:** Mark Bain (507443625075)
**Progress:** Ready for review {YYYY-MM-DD}. {What was done, where, what to check.} Session: {pct}% used (resets {reset_dt}).
```

**2. Update home project mirror** (`{PROJECT_DIR}/.claude/asana-mirror.md`):
Progress note only — do NOT change Section, Assignee, or Looper Status:
```
**Progress:** Work complete {YYYY-MM-DD} via studio-looper [{TARGET_PREFIX}]. Awaiting Mark's review. Session: {pct}% used (resets {reset_dt}).
```

**3. Sync both:**
```bash
python3 /media/data/dev/bain-studio/studio/sync.py --project {TARGET_PREFIX}
python3 /media/data/dev/bain-studio/studio/sync.py --project {PREFIX}
```

**4. Log and notify:**
```bash
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [{TARGET_PREFIX}/{PREFIX}] {TASK_ID} complete — moved to Review" >> ~/logs/task-looper.log
python3 /media/data/dev/bain-studio/studio/notifier.py \
  "{TASK_ID} ready for review: {task name}." \
  --priority normal --sender studio-task-looper --project {TARGET_PREFIX} --channel looper
```

**5. Output promise:**
```
<promise>{TASK_ID}_COMPLETE</promise>
```

### 4f — If blocked

**1. Update target mirror:**
```
**Looper Status:** Blocked
**Assignee:** Mark Bain (507443625075)
**Blockers:** {YYYY-MM-DD} — {What is blocking. What was attempted. What Mark needs to do.}
**Progress:** Blocked {YYYY-MM-DD}. {One sentence reason.} Session: {pct}% used (resets {reset_dt}).
```

**2. Update home project mirror:**
```
**Assignee:** Mark Bain (507443625075)
**Blockers:** {YYYY-MM-DD} — {same blocker text}
**Progress:** Blocked {YYYY-MM-DD} via studio-looper [{TARGET_PREFIX}]. {reason.} Session: {pct}% used (resets {reset_dt}).
```

**3. Sync both, log, notify:**
```bash
python3 /media/data/dev/bain-studio/studio/sync.py --project {TARGET_PREFIX}
python3 /media/data/dev/bain-studio/studio/sync.py --project {PREFIX}
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [{TARGET_PREFIX}/{PREFIX}] {TASK_ID} blocked: {reason}" >> ~/logs/task-looper.log
python3 /media/data/dev/bain-studio/studio/notifier.py \
  "{TASK_ID} blocked: {task name}. {reason}." \
  --priority high --sender studio-task-looper --project {TARGET_PREFIX} --channel looper
```

**4. Output promise:**
```
<promise>{TASK_ID}_BLOCKED</promise>
```

---

## How the loop works

After each promise, the stop hook reads `.claude/studio-looper.{session_id}.local.md` (the file
matching the firing session's own ID — never another session's), resolves the next task's project
dir from its prefix, and re-injects a prompt carrying `{TARGET_PREFIX}` forward. Queue is empty
when the body is empty — hook deletes its state file and notifies Mark.

---

## Guard rails

- Never mark a task DONE in Asana — move to Review (Looper Status) and reassign to Mark
- Never commit to main/master
- Never push secrets
- One commit per task
- If prefix lookup fails, mark blocked immediately
- Never start a second live run against the same `{TARGET_PREFIX}` — Step 1a's concurrency guard
  exists specifically to prevent two sessions racing on one queue. Use `--test` to test changes to
  this skill safely instead of running a second `--project SL` (or default) invocation.
- **A permission/access failure is never a reason to stop the loop.** If Edit/Write/Bash is denied on the project directory or mirror (missing `additionalDirectories` entry, git auth failure, sandboxed path, etc.), do not wait for interactive approval. Log a WARNING to `~/logs/task-looper.log`, mark the task Blocked with the specific access error as the reason, sync, and output the `_BLOCKED` promise so the queue advances to the next task. Skipping a task (or, if the whole project directory is inaccessible, every task under that prefix) is always correct; halting the loop is never correct.
- Output the promise only when genuinely complete or blocked
