---
name: pm-todos
description: Manage project todos from Claude's output. Use when the user says "create tasks", "add to todo", "update the todo list", "push to asana", "what's next", or "add these to the backlog". Writes prioritised tasks to TODO.md in the current project and optionally syncs to Asana. Also use to read and report what's next when the user asks.
argument-hint: [asana | todo | both]
allowed-tools: [Bash, Read, Write, Edit]
---

# Project Todos Skill

Manage project todos from Claude's output — write to TODO.md, push to Asana, or both.

## Arguments

- `asana` — push to Asana only
- `todo` — write to TODO.md only
- `both` — write to TODO.md and push to Asana

Default (no argument): write to TODO.md only.

Arguments provided: $ARGUMENTS

## "What's next?" mode

If the user asks "what's next?", "what should I work on?", or similar — read TODO.md and report the
top unchecked items with their descriptions. Do not create new tasks in this mode.

---

## Writing to TODO.md

### Format

TODO.md lives at the project root. Use this structure:

```markdown
# TODO

## High priority
- [ ] Task name
  Description of the task and what needs doing.

## Medium priority
- [ ] Task name
  Description.

## Low priority
- [ ] Task name
  Description.

## Done
- [x] Completed task name
```

### Steps

1. If TODO.md exists, read it first so you can append without duplicating existing items.
2. Extract tasks from the current conversation — typically Claude's most recent list of next steps.
3. Slot each task into the correct priority section.
4. Mark tasks with `- [ ]`. When Claude completes a task during a session, update it to `- [x]` and move it to the Done section.
5. Write the updated file.

---

## Pushing to Asana

### Token resolution

Always use the **bainbot PAT** (`ASANA_PAT` from `studio/.env`), never the human OAuth token. Resolve it once at the start of the Asana push:

```bash
ASANA_PAT=$(python3 -c "
from dotenv import load_dotenv; import os
from pathlib import Path
for p in ['studio/.env', '/media/data/dev/bain-studio/studio/.env']:
    if Path(p).exists():
        load_dotenv(p); break
print(os.getenv('ASANA_PAT', ''))
" 2>/dev/null)

if [ -z "$ASANA_PAT" ]; then
  echo "ERROR: ASANA_PAT not found in studio/.env"
  exit 1
fi
```

Use `$ASANA_PAT` in all subsequent curl calls. Never use `$ASANA_TOKEN`.

### Step 1 — Find the Asana project GID

Check in this order:

1. Read the project's CLAUDE.md for `ASANA_PROJECT_GID: <gid>`.
2. Check `.claude/asana-ids.json` for a GID.
3. If none found, ask the user.

### Step 2 — Find or create the TO DO section

```bash
# List sections
curl -s "https://app.asana.com/api/1.0/projects/{PROJECT_GID}/sections" \
  -H "Authorization: Bearer $ASANA_PAT"

# Create if missing
curl -s -X POST "https://app.asana.com/api/1.0/projects/{PROJECT_GID}/sections" \
  -H "Authorization: Bearer $ASANA_PAT" \
  -H "Content-Type: application/json" \
  -d '{"data": {"name": "TO DO"}}'
```

### Step 3 — Create each task in priority order

```bash
# Create task (assigned to bainbot — sync will show it in the mirror)
BAINBOT_GID=$(python3 -c "
from dotenv import load_dotenv; import os
from pathlib import Path
for p in ['studio/.env', '/media/data/dev/bain-studio/studio/.env']:
    if Path(p).exists():
        load_dotenv(p); break
print(os.getenv('ASANA_BAINBOT_GID', ''))
" 2>/dev/null)

curl -s -X POST "https://app.asana.com/api/1.0/tasks" \
  -H "Authorization: Bearer $ASANA_PAT" \
  -H "Content-Type: application/json" \
  -d "{
    \"data\": {
      \"name\": \"TASK NAME\",
      \"notes\": \"TASK DESCRIPTION\",
      \"projects\": [\"PROJECT_GID\"],
      \"assignee\": \"$BAINBOT_GID\"
    }
  }"

# Move into TO DO section
curl -s -X POST "https://app.asana.com/api/1.0/sections/{TODO_SECTION_GID}/addTask" \
  -H "Authorization: Bearer $ASANA_PAT" \
  -H "Content-Type: application/json" \
  -d "{\"data\": {\"task\": \"TASK_GID\"}}"

# Add created-by comment
curl -s -X POST "https://app.asana.com/api/1.0/tasks/{TASK_GID}/stories" \
  -H "Authorization: Bearer $ASANA_PAT" \
  -H "Content-Type: application/json" \
  -d "{\"data\": {\"text\": \"Created by Claude Code on $(date '+%Y-%m-%d') via the pm-todos skill.\"}}"
```

### Step 4 — Report back

Output: number of tasks created, project link, one line per task with Asana URL.

---

## Error handling

- Task creation failure: log and continue — don't abort the batch.
- No TODO.md: create it from scratch.
- Asana 401: tell the user the token in `~/.claude/settings.json` (env.ASANA_TOKEN) may have expired.
- TO DO section not found and can't be created: place tasks in project root and warn.
