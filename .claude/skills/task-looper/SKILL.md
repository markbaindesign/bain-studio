---
name: task-looper
description: Work through outstanding tasks assigned to BainBot in the current project's Asana mirror. Self-driving via stop hook — sets up a task queue, works each task to completion or a clear blocker, raises PRs, and loops automatically until the queue is empty.
allowed-tools:
  - Read
  - Edit
  - Write
  - Bash
  - WebSearch
  - WebFetch
---

# BD Task Looper

Sets up a self-driving task queue backed by a stop hook. Works one task at a time. Outputs a completion promise when done or blocked; the hook advances the queue and re-injects the next task automatically.

---

## Step 0 — Check for --at flag

If the arguments contain `--at TIME PREFIX` (e.g. `/task-looper --at 20:10 WTF`):

1. Look up the project path from `studio/projects.json` by matching the prefix against each project's `CLAUDE.md`:

```bash
python3 - <<'EOF'
import json, subprocess, os, sys

prefix = sys.argv[1].upper()
projects = json.load(open("/media/data/dev/bain-studio/studio/projects.json"))
for p in projects:
    claude_md = os.path.join(p["path"], "CLAUDE.md")
    if os.path.exists(claude_md):
        content = open(claude_md).read()
        if f"ASANA_TASK_PREFIX: {prefix}" in content:
            print(p["path"])
            sys.exit(0)
print("NOT_FOUND")
EOF
python3 - {PREFIX}
```

2. If `NOT_FOUND`, abort: "No project with prefix {PREFIX} found in projects.json."

3. If found, schedule the run. Try `at` first; fall back to a Python sleep script if `at` is unavailable:

```bash
if command -v at &>/dev/null; then
    echo "cd {PROJECT_PATH} && claude -p '/task-looper'" | at {TIME}
else
    python3 - <<'EOF'
import time, subprocess, sys
from datetime import datetime

hh, mm = map(int, sys.argv[1].split(":"))
project_path = sys.argv[2]
target = datetime.now().replace(hour=hh, minute=mm, second=0, microsecond=0)
delay = (target - datetime.now()).total_seconds()
if delay <= 0:
    print(f"ERROR: {sys.argv[1]} is in the past.")
    sys.exit(1)

script = f"""import time, subprocess, os
time.sleep({delay})
subprocess.run(["claude", "-p", "/task-looper"], cwd="{project_path}")
"""
with open("/tmp/task-looper-scheduled.py", "w") as f:
    f.write(script)
print(f"Scheduled via Python sleep ({int(delay)}s). Log: ~/logs/task-looper.log")
EOF
    python3 - {TIME} {PROJECT_PATH}
    nohup python3 /tmp/task-looper-scheduled.py >> ~/logs/task-looper.log 2>&1 &
    echo "PID: $!"
fi
```

4. Confirm: "Scheduled /task-looper for {PREFIX} ({PROJECT_PATH}) at {TIME}." Then stop — do not proceed to Step 1.

---

## Logging

All loggable events are written to `~/logs/task-looper.log` using inline `echo` appends. Format matches `studio/sync.log`:

```bash
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [{PREFIX}] message" >> ~/logs/task-looper.log
```

Replace `{PREFIX}` with the project prefix (e.g. `BD`, `WTF`). Until the prefix is known, use `TASK-LOOPER`.

Log these events (examples):
- Session start: `[BD] Session started — 3 tasks in queue: BD-039 BD-040 BD-041`
- Session end: `[BD] Session ended — queue empty`
- Task started: `[BD] BD-039 started: Add custom icons for all CPTs`
- Branch created: `[BD] git checkout -b feature/bd-039-add-custom-icons-cpts`
- Commit: `[BD] commit: "Set distinct dashicons for each custom post type" (register.php)`
- Push: `[BD] pushed feature/bd-039-add-custom-icons-cpts`
- PR raised: `[BD] PR: https://github.com/...`
- Task complete: `[BD] BD-039 complete`
- Task blocked: `[BD] BD-039 blocked: {one-sentence reason}`
- Queue remaining: `[BD] queue: 5 tasks remaining: BD-040 BD-041 BD-042 BD-043 BD-044`
- Queue empty: `[BD] queue: empty`
- Usage at start: `[BD] usage-start: 35% — resets 2026-07-01 04:00`
- Usage at end: `[BD] usage-end: 38% — resets 2026-07-01 04:00`
- Sync call: `[BD] sync.py --project BD → exit 0`
- Notifier call: `[BD] notify: {message text}`
- Error: `[BD] ERROR: {command} exited {code} — {stderr}`

For errors (non-zero exit from any bash command), log before taking any recovery action.

---

## Step 1 — Load project context

Read `CLAUDE.md` in the current working directory. Extract:
- Project name and prefix (e.g. BD, MCF, NORE)
- Tech stack and build/run instructions
- Active project path (confirm you are in it)
- Any standing instructions relevant to development

---

## Step 1b — Sync from Asana

Pull fresh task data from Asana before reading the mirror. This picks up any comments Mark has added, tasks that have been unblocked, or notes that resolve previous blockers.

```bash
cd /media/data/dev/bain-studio && python3 studio/sync.py --project {PREFIX}
```

Then read `.claude/asana-mirror.md` and check for any tasks that were previously blocked but now have new information in their `**Comments:**` or `**Notes:**` fields that resolves the blocker.

---

## Step 2 — Build the queue

Read `.claude/asana-mirror.md`. Extract all tasks where:
- `**Assignee:**` contains `BainBot`
- `**Section:**` is NOT `DONE`

If none found, log and notify via Hermes and stop:
```bash
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [{PREFIX}] Session ended — no outstanding BainBot tasks" >> ~/logs/task-looper.log
python3 /media/data/dev/bain-studio/studio/notifier.py \
  "task-looper: no outstanding BainBot tasks in {Project}." \
  --priority normal --sender task-looper --project {PREFIX}
```

Order the queue:
1. Tasks with a `**Due:**` date — soonest first
2. Tasks with no unresolved `**Dependencies:**`
3. Everything else — mirror order

---

## Step 3 — Write the state file

Write `.claude/bd-task-looper.local.md`. The first task in the queue goes in `current_task`; the rest go in the body, one ID per line.

```
---
session_id: __pending__
current_task: {FIRST_TASK_ID}
iteration: 0
max_iterations: 30
project_prefix: {PREFIX}
project_dir: {ABSOLUTE_PATH_TO_PROJECT}
---
{SECOND_TASK_ID}
{THIRD_TASK_ID}
...
```

If there is only one task, the body is empty.

Notify via Hermes that the run is starting:
```bash
python3 /media/data/dev/bain-studio/studio/notifier.py \
  "task-looper starting on {Project} — {N} tasks: {IDs}" \
  --priority normal --sender task-looper --project {PREFIX}
```

Log session start:
```bash
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [{PREFIX}] Session started — {N} tasks in queue: {IDs}" >> ~/logs/task-looper.log
```

---

## Step 4 — Work the first task

Work the task in `current_task`. The stop hook will drive all subsequent tasks automatically.

### 4a. Create a feature branch

Derive a slug from the task name: lowercase, spaces to hyphens, strip special characters. Do not include the `feature/` prefix — git flow adds that.

```bash
git flow feature start {prefix-id}-{slug}
```

Example: `BD-012 — Fix typewriter lines` → `git flow feature start bd-012-fix-typewriter-lines` → creates `feature/bd-012-fix-typewriter-lines`

git flow branches from the configured develop branch automatically. If `git flow feature start` fails (git flow not initialised), fall back to:

```bash
git checkout develop && git pull && git checkout -b feature/{prefix-id}-{slug}
```

Log task start, branch creation, and usage at start:
```bash
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [{PREFIX}] {TASK_ID} started: {task name}" >> ~/logs/task-looper.log
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [{PREFIX}] git flow feature start {prefix-id}-{slug}" >> ~/logs/task-looper.log
python3 - <<'PYEOF'
import json, datetime
from pathlib import Path
rl = Path.home() / ".claude/ratelimit-current.json"
if rl.exists():
    data = json.loads(rl.read_text())
    pct = data.get("current_pct", "?")
    reset_ts = data.get("reset_ts")
    reset_dt = datetime.datetime.fromtimestamp(reset_ts).strftime("%Y-%m-%d %H:%M") if reset_ts else "unknown"
else:
    pct, reset_dt = "?", "unknown"
log = Path.home() / "logs/task-looper.log"
ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
log.open("a").write(f"{ts} INFO    [{PREFIX}] usage-start: {pct}% — resets {reset_dt}\n")
PYEOF
```

### 4b. Understand the task

Read the task's `**Notes:**` field fully. If it references files, read them. If it references a URL, fetch it. Explore the codebase as needed.

Ask yourself: *Do I have everything I need to complete this without guessing?*

### 4c. Work

Do the work. Use your full judgment and knowledge of the tech stack.

- Commit as logical units: `git add <specific files> && git commit -m "..."`
- Commit messages describe what changed and why — not the task number
- Never commit `.env` files, secrets, or large binaries
- Never commit directly to main/master

After each commit, log it:
```bash
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [{PREFIX}] commit: \"{commit message}\" ({files changed})" >> ~/logs/task-looper.log
```

If any bash command exits non-zero, log the error before recovering:
```bash
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [{PREFIX}] ERROR: {command} exited {code} — {stderr}" >> ~/logs/task-looper.log
```

### 4d. Assess completion

**Complete** means: the described problem is solved, the change works, nothing newly broken.

**Blocked** means any of:
- Need information only Mark can provide (credential, decision, preference)
- External dependency not yet in place
- Task is ambiguous and completing it would require guessing at intent
- Discovered a prerequisite that must be resolved first

### 4e — If complete

Read the current rate limit usage before updating the mirror:
```bash
python3 - <<'PYEOF'
import json, datetime
from pathlib import Path
rl = Path.home() / ".claude/ratelimit-current.json"
if rl.exists():
    data = json.loads(rl.read_text())
    pct = data.get("current_pct", "?")
    reset_ts = data.get("reset_ts")
    reset_dt = datetime.datetime.fromtimestamp(reset_ts).strftime("%Y-%m-%d %H:%M") if reset_ts else "unknown"
else:
    pct, reset_dt = "?", "unknown"
log = Path.home() / "logs/task-looper.log"
ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
log.open("a").write(f"{ts} INFO    [{PREFIX}] usage-end: {pct}% — resets {reset_dt}\n")
print(f"usage:{pct}:{reset_dt}")
PYEOF
```

Capture the printed `usage:{pct}:{reset_dt}` line from stdout and include it in the Progress update below.

Update the mirror:
- Set `**Section:**` to `DONE`
- Set `**Progress:**` to: `Completed {YYYY-MM-DD}. {One or two sentences: what changed, where, what it does.} Session: {pct}% used (resets {reset_dt}).`

Run sync:
```bash
cd /media/data/dev/bain-studio && python3 studio/sync.py --project {PREFIX}
```

Log sync call:
```bash
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [{PREFIX}] sync.py --project {PREFIX} → exit $?" >> ~/logs/task-looper.log
```

Push branch and raise PR:
```bash
git push -u origin feature/{prefix-id}-{slug}
gh pr create \
  --title "{Task name}" \
  --body "$(cat <<'EOF'
## Task
{Task local ID} — {Task name}

## What was done
{Solution: what changed, where, and why}

## Test notes
{How to verify — specific steps or observations}

🤖 task-looper — [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Log push, PR, and completion:
```bash
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [{PREFIX}] pushed feature/{prefix-id}-{slug}" >> ~/logs/task-looper.log
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [{PREFIX}] PR: {pr_url}" >> ~/logs/task-looper.log
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [{PREFIX}] {TASK_ID} complete" >> ~/logs/task-looper.log
```

Log queue state:
```bash
python3 - <<'PYEOF'
import datetime
from pathlib import Path
PREFIX = "{PREFIX}"
state_file = Path.cwd() / f".claude/{PREFIX.lower()}-task-looper.local.md"
if state_file.exists():
    parts = state_file.read_text().split("---", 2)
    body = parts[2].strip() if len(parts) >= 3 else ""
    remaining = [l.strip() for l in body.splitlines() if l.strip()]
    msg = f"queue: {len(remaining)} tasks remaining: {' '.join(remaining)}" if remaining else "queue: empty"
else:
    msg = "queue: state file not found"
log = Path.home() / "logs/task-looper.log"
ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
log.open("a").write(f"{ts} INFO    [{PREFIX}] {msg}\n")
PYEOF
```

Notify:
```bash
python3 /media/data/dev/bain-studio/studio/notifier.py \
  "{ID} complete: {task name}. PR at {url or 'branch pushed'}." \
  --priority normal --sender task-looper --project {PREFIX}
```

Log the notify call:
```bash
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [{PREFIX}] notify: {ID} complete: {task name}. PR at {url}." >> ~/logs/task-looper.log
```

Then output the completion promise:
```
<promise>{TASK_ID}_COMPLETE</promise>
```

### 4f — If blocked

Check out back to the git flow develop branch (leave the feature branch — partial work is not lost):
```bash
git checkout "$(git config gitflow.branch.develop 2>/dev/null || echo develop)"
```

Read the current rate limit usage before updating the mirror:
```bash
python3 - <<'PYEOF'
import json, datetime
from pathlib import Path
rl = Path.home() / ".claude/ratelimit-current.json"
if rl.exists():
    data = json.loads(rl.read_text())
    pct = data.get("current_pct", "?")
    reset_ts = data.get("reset_ts")
    reset_dt = datetime.datetime.fromtimestamp(reset_ts).strftime("%Y-%m-%d %H:%M") if reset_ts else "unknown"
else:
    pct, reset_dt = "?", "unknown"
log = Path.home() / "logs/task-looper.log"
ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
log.open("a").write(f"{ts} INFO    [{PREFIX}] usage-end: {pct}% — resets {reset_dt}\n")
print(f"usage:{pct}:{reset_dt}")
PYEOF
```

Capture the printed `usage:{pct}:{reset_dt}` line from stdout.

Update the mirror — both fields:
```
**Blockers:** {YYYY-MM-DD} — {What is blocking. What information or decision is needed. Who can resolve it. What was attempted.}
**Progress:** Blocked {YYYY-MM-DD}. {Same reason in one or two sentences — this is what gets posted as an Asana comment.} Session: {pct}% used (resets {reset_dt}).
```

Run sync:
```bash
cd /media/data/dev/bain-studio && python3 studio/sync.py --project {PREFIX}
```

Log sync call:
```bash
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [{PREFIX}] sync.py --project {PREFIX} → exit $?" >> ~/logs/task-looper.log
```

Log the blocker and queue state:
```bash
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [{PREFIX}] {TASK_ID} blocked: {one-sentence reason}" >> ~/logs/task-looper.log
python3 - <<'PYEOF'
import datetime
from pathlib import Path
PREFIX = "{PREFIX}"
state_file = Path.cwd() / f".claude/{PREFIX.lower()}-task-looper.local.md"
if state_file.exists():
    parts = state_file.read_text().split("---", 2)
    body = parts[2].strip() if len(parts) >= 3 else ""
    remaining = [l.strip() for l in body.splitlines() if l.strip()]
    msg = f"queue: {len(remaining)} tasks remaining: {' '.join(remaining)}" if remaining else "queue: empty"
else:
    msg = "queue: state file not found"
log = Path.home() / "logs/task-looper.log"
ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
log.open("a").write(f"{ts} INFO    [{PREFIX}] {msg}\n")
PYEOF
```

Notify:
```bash
python3 /media/data/dev/bain-studio/studio/notifier.py \
  "{ID} blocked: {task name}. {One sentence blocker summary}. Branch {branch-name} has partial work." \
  --priority high --sender task-looper --project {PREFIX}
```

Log the notify call:
```bash
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO    [{PREFIX}] notify (high): {ID} blocked: {one-sentence reason}." >> ~/logs/task-looper.log
```

Then output the blocked promise:
```
<promise>{TASK_ID}_BLOCKED</promise>
```

---

## How the loop works

After you output a promise, the stop hook:
1. Reads the state file to find the next task
2. Advances the queue (removes the completed/blocked task, promotes the next)
3. Re-injects a fresh prompt for the next task
4. When the queue is empty, deletes the state file and allows the session to end

You do not need to manage the queue. Just work one task, output the promise, and stop.

---

## Guard rails

- **Never guess at requirements.** Ambiguous = blocked, not complete.
- **Never commit to main/master.** All work in feature branches.
- **Never push secrets.** Check before every commit.
- **A working change is the solution.** A PR is not.
- **Never touch tasks outside your queue.** Do not modify tasks assigned to Mark.
- **The Law of the Gate.** PRs are for Mark's review. Never merge.
- **One task per branch.** No mixing.
- **Partial work is not lost.** Leave the branch. Document the blocker clearly.
- **Output the promise only when true.** Not to escape. The loop continues until genuine completion or a genuine blocker.
