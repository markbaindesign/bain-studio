---
name: focus
description: Mid-day project context switch. Run from the bain-studio directory with a project prefix (e.g. /focus MCF). Looks up the project path and produces a full /recap brief without needing to cd there first.
allowed-tools: [Read, Bash]
---

# Focus

Switch focus to a project mid-day. Run from `/media/data/dev/bain-studio` with a prefix argument.

Usage: `/focus MCF` or `/focus NORE`

## Steps

### 1. Parse the argument

The argument is a project prefix (e.g. `MCF`, `NORE`, `WTF`). If no argument provided, list active projects and ask which one.

### 2. Look up the project path

Read `studio/projects.json`. Find the entry whose `CLAUDE.md` contains `ASANA_TASK_PREFIX: {PREFIX}`.

```bash
python3 -c "
import json
from pathlib import Path
projects = json.loads(Path('studio/projects.json').read_text())
for p in projects:
    path = Path(p['path'])
    claude_md = path / 'CLAUDE.md'
    if claude_md.exists() and 'ASANA_TASK_PREFIX: {PREFIX}' in claude_md.read_text():
        print(p['path'])
        break
"
```

If not found, list available prefixes and abort.

### 3. Run recap for that project

Change to the project directory and run the same steps as `/recap`:

1. Git context — branch, last 3 commits, dirty flag
2. Asana state — read `{path}/.claude/asana-mirror.md`
3. Inbox — check `{path}/.claude/inbox/` for unread messages
4. Open questions — read `{path}/.claude/open-questions.md`
5. Synthesise next action

### 4. Output

Same format as `/recap`:

```
## Recap — {PROJECT_NAME} — {YYYY-MM-DD HH:MM}

### Git
Branch: {branch} {[DIRTY] if uncommitted changes}
Recent: {last 3 commits, one per line}

### In progress
{list or "None"}

### Blocked
{list or "None"}

### Inbox
{list or "Clear"}

### Open questions
{list or "None"}

### Next action
→ {synthesised suggestion}
```
