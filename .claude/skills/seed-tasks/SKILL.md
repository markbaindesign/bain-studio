---
name: seed-tasks
description: Create initial tasks in an Asana project via the bainbot API. Standalone step — callable directly or by /commission. Args: project-gid "Task 1" "Task 2" ...
allowed-tools: [Bash, Read]
---

# Seed Tasks

Create tasks in an Asana project using the bainbot PAT.

Arguments: $ARGUMENTS
- First arg: Asana project GID
- Remaining args: task names (quoted strings), OR pass `--from-spec {path}` to extract tasks from a spec file

## Step 1 — Load credentials

```bash
source /media/data/dev/bain-studio/studio/.env
```

The bainbot token is `$ASANA_PAT`. The workspace GID is `$ASANA_WORKSPACE_GID`.

## Step 2 — Get tasks

**If args are quoted task strings:** use them directly.

**If `--from-spec {path}` is passed:** read the spec file. Extract task names from:
- Any `### Phase` section headers (use "Phase N — {name}" as a task)
- Bulleted lists directly under Phase headers
- Any `## Initial tasks` section

Deduplicate and limit to 20 tasks — if more, take the first 20 and note the truncation.

## Step 3 — Create each task

For each task name, POST to Asana:

```bash
curl -s -X POST "https://app.asana.com/api/1.0/tasks" \
  -H "Authorization: Bearer $ASANA_PAT" \
  -H "Content-Type: application/json" \
  -d "{\"data\": {\"name\": \"{task_name}\", \"projects\": [\"{project_gid}\"]}}"
```

Check each response for `"gid"` — if missing, report the error and continue with remaining tasks.

## Step 4 — Report

```
seed-tasks: {project_gid}
  Created {N} tasks:
  - {task 1}
  - {task 2}
  ...
  {N errors if any}
```
