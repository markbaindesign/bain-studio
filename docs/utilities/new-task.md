---
tags: [utility, asana, tasks, workflow]
god: hermes
command: python3 studio/sync.py --create-task
description: Create a new Asana task from the CLI or during a Claude session. Assigns a local ID, places it in the correct section, and appends it to the local mirror immediately.
---

# New Task

Creates a task in Asana via bainbot, assigns a local ID (e.g. `NORE-042`), places it in the specified section, and appends it to the project's local mirror file — all in one step.

## Two entry points

### 1. CLI (from your terminal)

```bash
studio-task NORE "Fix robots.txt on staging"
studio-task NORE "Fix robots.txt on staging" --task-section "DOING"
studio-task NORE "Fix robots.txt on staging" --task-notes "Blocking SEO crawl of staging" --task-due 2026-07-01
```

`studio-task` is an alias for `python3 /media/data/dev/bain-studio/studio/sync.py --create-task --project`.

### 2. During a Claude session

Tell Claude to create a task and it will run:

```bash
python3 /media/data/dev/bain-studio/studio/sync.py \
  --create-task \
  --project NORE \
  --task-name "Fix robots.txt on staging" \
  --task-section "NEXT UP" \
  --task-notes "Blocking SEO crawl of staging site"
```

## Full options

```
--project PREFIX       Project prefix (required): NORE, BSTD, MCF, etc.
--task-name NAME       Task title (required)
--task-section NAME    Section to place in (default: NEXT UP)
                       Must match an existing Asana section name exactly
--task-notes TEXT      Task description / notes (optional)
--task-due YYYY-MM-DD  Due date (optional)
--dry-run              Preview without creating anything
```

## What it does

1. Resolves the section GID from Asana for the target project
2. Creates the task in Asana via bainbot PAT
3. Moves it to the specified section
4. Assigns the next local ID in sequence (reads/writes `asana-ids.json`)
5. Writes the local ID back to the Asana custom field
6. Appends a full task block to the project's `.claude/asana-mirror.md`

The task is live in Asana and visible in the mirror immediately - no sync run needed.

## Available sections

Sections vary by project. Common ones: `DOING`, `NEXT UP`, `TO DO`, `STALLED`, `SOMEDAY/MAYBE`.

To see sections for a project, check its mirror or Asana board. The `--task-section` value must match exactly (case-insensitive).

## Notes

- All tasks are assigned to bainbot (not Mark) - consistent with the mirror workflow
- The mirror entry will be overwritten on the next full sync with fresh data from Asana, but the task GID and local ID are preserved
- Use `--dry-run` to preview what would be created without hitting Asana
