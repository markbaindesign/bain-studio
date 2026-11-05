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
--task-assignee GID    Assignee (default: BainBot). 'me' uses ASANA_USER_GID
--task-depends-on GID  A task the new one blocks. If linking fails, the task
                       is still created but the command exits 1 and says so
--dry-run              Preview without creating anything
```

## What it does

1. Resolves the section GID from Asana for the target project
2. Creates the task in Asana via bainbot PAT
3. Moves it to the specified section
4. Assigns the next local ID in sequence (reads/writes `asana-ids.json`)
5. Writes the local ID back to the Asana custom field
6. Appends a full task block to the project's `asana-mirror.md`

The task is live in Asana and visible in the mirror immediately - no sync run needed.

## Available sections

Sections vary by project. Common ones: `DOING`, `NEXT UP`, `TO DO`, `STALLED`, `SOMEDAY/MAYBE`.

To see sections for a project, check its mirror or Asana board. The `--task-section` value must match exactly (case-insensitive).

## Description length is enforced

`--task-notes` is the task's **description**. On `--create-task` it is refused over **1,200
characters** and nothing is sent to Asana:

```
ERROR Not creating task: description is 3510 chars, over the 1200-char limit. State what the
task is, what done looks like and where the work is. The history, the alternatives and the
session narrative belong in a commit message or a comment.
```

A description says three things: what the task is, what done looks like, and where the work
is (paths, URLs, GIDs). Per [ADR 022](../adr/022-asana-tasks-carry-their-own-context.md) it
carries its own context, so repeat the client, page or section rather than leaning on the
section or a parent task.

**Never in a description:** how the problem arose, what was ruled out, alternatives weighed,
a session narrative, or dates of past sessions. That belongs in the commit message, where
`git log` reaches it, or in a comment. The limit is loose on purpose — the studio median is
about 500 characters, and the walls of text that prompted it ran 2,000–3,500.

Only descriptions written through `sync.py` are checked. A task that arrives by Asana's own
email intake (a forwarded alert, a vendor email) never passes through here and is unaffected
however long it is.

On `--update-task` the limit is softer, so that it cannot trap a correction: an over-limit
description is refused only when it is **no shorter** than the one it replaces. A 1,400-char
rewrite of a 3,500-char description goes through, and is logged as a correction.

The description is read-only in the mirror. To correct one, use `--update-task`, which
replaces it wholesale — read the current text first:

```bash
python3 studio/sync.py --get-task BSTD-856
python3 studio/sync.py --update-task --task-gid 1220199946249933 \
  --task-notes "Corrected description."
```

## Notes

- Tasks are assigned to bainbot unless `--task-assignee` says otherwise - use `--task-assignee me` for a task Mark has to do, so it lands in his My Tasks
- The mirror entry will be overwritten on the next full sync with fresh data from Asana, but the task GID and local ID are preserved
- Use `--dry-run` to preview what would be created without hitting Asana
- To add subtasks under an existing task, see [new-subtask](new-subtask.md)
