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

### Step 1 — Find the Asana project GID

Check in this order:

1. Read the project's CLAUDE.md for `ASANA_PROJECT_GID: <gid>`.
2. Check `.claude/` memory files for an Asana GID.
3. Search by name: list all projects and match against the current directory name (case-insensitive, partial match OK).
4. If none found, ask the user.

```bash
curl -s "https://app.asana.com/api/1.0/projects?workspace=$ASANA_WORKSPACE_GID&opt_fields=name,gid" \
  -H "Authorization: Bearer $ASANA_TOKEN"
```

### Step 2 — Find or create the TO DO section

```bash
# List sections
curl -s "https://app.asana.com/api/1.0/projects/{PROJECT_GID}/sections" \
  -H "Authorization: Bearer $ASANA_TOKEN"

# Create if missing
curl -s -X POST "https://app.asana.com/api/1.0/projects/{PROJECT_GID}/sections" \
  -H "Authorization: Bearer $ASANA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data": {"name": "TO DO"}}'
```

### Step 3 — Create each task in priority order

```bash
# Create task
curl -s -X POST "https://app.asana.com/api/1.0/tasks" \
  -H "Authorization: Bearer $ASANA_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"data\": {
      \"name\": \"TASK NAME\",
      \"notes\": \"TASK DESCRIPTION\",
      \"projects\": [\"PROJECT_GID\"],
      \"assignee\": \"$ASANA_USER_GID\"
    }
  }"

# Move into TO DO section
curl -s -X POST "https://app.asana.com/api/1.0/sections/{TODO_SECTION_GID}/addTask" \
  -H "Authorization: Bearer $ASANA_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"data\": {\"task\": \"TASK_GID\"}}"

# Add created-by comment
curl -s -X POST "https://app.asana.com/api/1.0/tasks/{TASK_GID}/stories" \
  -H "Authorization: Bearer $ASANA_TOKEN" \
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
