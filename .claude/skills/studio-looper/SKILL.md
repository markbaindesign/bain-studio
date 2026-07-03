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

## Usage

```
/studio-looper              — start the queue
/studio-looper --for 2h     — run for up to 2 hours
/studio-looper --use 10%    — consume at most 10% of quota
/studio-looper --yes        — skip queue confirmation
```

---

## Step 0 — Parse flags

Same as task-looper: `--for DURATION`, `--use N%`. Calculate deadline/stop threshold.
Store as `FOR_DEADLINE` and `STOP_AT_PCT`.

---

## Step 1 — Confirm CWD

```bash
pwd
```

Must be `/media/data/dev/bain-studio`. If not, stop: "studio-looper must be run from the studio root."

---

## Step 1b — Sync Studio Looper project

```bash
python3 studio/sync.py --project SL
```

If this fails because the SL project GID is not configured, stop and tell Mark to complete
the setup in `studio/looper/CLAUDE.md`.

---

## Step 1c — Check deadline and usage headroom

**Deadline check:**
```bash
python3 - <<'PYEOF'
import datetime
from pathlib import Path

state = Path(".claude/studio-looper.local.md")
if not state.exists():
    exit(0)

deadline = None
for line in state.read_text().split("\n"):
    if line.startswith("deadline:"):
        val = line.split(":", 1)[1].strip()
        if val:
            deadline = datetime.datetime.fromisoformat(val)
        break

if deadline and datetime.datetime.now() >= deadline:
    print(f"PAST_DEADLINE:{deadline.strftime('%H:%M')}")
PYEOF
```

If `PAST_DEADLINE:{TIME}`: log, notify, stop without outputting a promise.

**Usage check:**
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

state = Path(".claude/studio-looper.local.md")
stop_at = None
if state.exists():
    for line in state.read_text().split("\n"):
        if line.startswith("stop_at_pct:"):
            val = line.split(":", 1)[1].strip()
            if val:
                try: stop_at = float(val)
                except ValueError: pass
            break

if stop_at is not None and isinstance(pct, (int, float)) and pct >= stop_at:
    print(f"QUOTA_SPENT:{pct}:{stop_at}")
else:
    print(f"usage:{pct}:{reset_str}")
PYEOF
```

- `QUOTA_SPENT`: log, notify, stop
- `usage:{pct}:{reset_str}`: log and continue

---

## Step 2 — Build queue from SL mirror

Read `studio/looper/.claude/asana-mirror.md`. Extract all tasks where:
- `**Looper Status:** Queue`

Tasks appear in mirror order, which reflects their drag order in Asana = Mark's priority.

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

Present the queue for confirmation (unless `--yes`):
```
Studio Looper — {N} tasks queued:

  1. MCF-007  [High] — Add blog category filter          (MCF)
  2. NORE-029 [High] — Fix broken contact form           (NORE)
  3. BSTD-021 [Low]  — Add API cost tracker              (BSTD)

Proceed? Press Enter to confirm, or list IDs to skip (e.g. "NORE-029 BSTD-021"):
```

---

## Step 3 — Write state file

Write `.claude/studio-looper.local.md`. First task in `current_task`, rest in body:

```
---
session_id: __pending__
current_task: {FIRST_TASK_ID}
iteration: 0
max_iterations: 30
deadline: {DEADLINE_ISO}
stop_at_pct: {STOP_AT_PCT}
---
{SECOND_TASK_ID}
{THIRD_TASK_ID}
...
```

In the SL mirror, set `current_task`'s **Looper Status** to `In Progress`, then sync:
```bash
# Edit studio/looper/.claude/asana-mirror.md: change Looper Status from Queue → In Progress
python3 studio/sync.py --project SL
```

Notify and log session start:
```bash
python3 studio/notifier.py \
  "studio-looper starting — {N} tasks: {IDs}" \
  --priority normal --sender studio-task-looper --project SL
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [SL] Session started — {N} tasks: {IDs}" >> ~/logs/task-looper.log
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
log.open("a").write(f"{ts} INFO    [SL] usage-end: {pct}% — resets {reset_dt}\n")
print(f"usage:{pct}:{reset_dt}")
PYEOF
```

**1. Update SL mirror** (`/media/data/dev/bain-studio/studio/looper/.claude/asana-mirror.md`):
```
**Looper Status:** Review
**Assignee:** Mark Bain (507443625075)
**Progress:** Ready for review {YYYY-MM-DD}. {What was done, where, what to check.} Session: {pct}% used (resets {reset_dt}).
```

**2. Update home project mirror** (`{PROJECT_DIR}/.claude/asana-mirror.md`):
Progress note only — do NOT change Section, Assignee, or Looper Status:
```
**Progress:** Work complete {YYYY-MM-DD} via studio-looper. Awaiting Mark's review in Studio Looper project. Session: {pct}% used (resets {reset_dt}).
```

**3. Sync both:**
```bash
python3 /media/data/dev/bain-studio/studio/sync.py --project SL
python3 /media/data/dev/bain-studio/studio/sync.py --project {PREFIX}
```

**4. Log and notify:**
```bash
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [SL/{PREFIX}] {TASK_ID} complete — moved to Review" >> ~/logs/task-looper.log
python3 /media/data/dev/bain-studio/studio/notifier.py \
  "{TASK_ID} ready for review: {task name}." \
  --priority normal --sender studio-task-looper --project SL
```

**5. Output promise:**
```
<promise>{TASK_ID}_COMPLETE</promise>
```

### 4f — If blocked

**1. Update SL mirror:**
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
**Progress:** Blocked {YYYY-MM-DD} via studio-looper. {reason.} Session: {pct}% used (resets {reset_dt}).
```

**3. Sync both, log, notify:**
```bash
python3 /media/data/dev/bain-studio/studio/sync.py --project SL
python3 /media/data/dev/bain-studio/studio/sync.py --project {PREFIX}
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [SL/{PREFIX}] {TASK_ID} blocked: {reason}" >> ~/logs/task-looper.log
python3 /media/data/dev/bain-studio/studio/notifier.py \
  "{TASK_ID} blocked: {task name}. {reason}." \
  --priority high --sender studio-task-looper --project SL
```

**4. Output promise:**
```
<promise>{TASK_ID}_BLOCKED</promise>
```

---

## How the loop works

After each promise, the stop hook reads `.claude/studio-looper.local.md`, resolves the next
task's project dir from its prefix, and re-injects a prompt. Queue is empty when the body is
empty — hook deletes state file and notifies Mark.

---

## Guard rails

- Never mark a task DONE in Asana — move to Review (Looper Status) and reassign to Mark
- Never commit to main/master
- Never push secrets
- One commit per task
- If prefix lookup fails, mark blocked immediately
- Output the promise only when genuinely complete or blocked
