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

## Follow-up tasks

Work left for later is created as a follow-up of the task it came from:

```bash
python3 /media/data/dev/bain-studio/studio/sync.py --create-task \
  --follow-up-of NORE-041 --task-name "Add hreflang tags to staging" \
  --task-notes "Done when every staging page carries hreflang."
```

This is the API's version of Asana's "Create follow-up task" menu item, which has no endpoint
of its own. A link in a description leaves nothing on the task it names, hence the comment on
the original. Verified on SLT, 2026-11-17.

## Full options

```
--project PREFIX       Project prefix: NORE, BSTD, MCF, etc. Required unless
                       --follow-up-of names a task with a local ID
--task-name NAME       Task title (required)
--task-section NAME    Section to place in (default: NEXT UP)
                       Must match an existing Asana section name exactly
--task-notes TEXT      Task description / notes (optional)
--task-due YYYY-MM-DD  Due date (optional)
--task-assignee GID    Assignee (default: BainBot). 'me' uses ASANA_USER_GID
--task-depends-on GID  A task the new one blocks. If linking fails, the task
                       is still created but the command exits 1 and says so
--follow-up-of TASK    The task this one follows up (local ID, GID or URL).
                       The description opens "Follow-up to {ID}." linking that
                       task, and the original gets a silent "Follow-up: {new ID}"
                       comment linking back
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

A task created for work Claude is doing in the current session goes in `DOING`; a follow-up
or anything for later keeps the default, `NEXT UP`.

To see sections for a project, check its mirror or Asana board. The `--task-section` value must match exactly (case-insensitive).

## Title prefixes are refused

A title is the task itself, as a plain sentence. `--create-task`, `--update-task --task-name`
and `--create-subtask` refuse a title that opens with a label (a short run before `: `, or a
leading `[...]`) and send nothing to Asana:

```
ERROR Not creating task: title opens with the label 'sync.py:'. A title is the task itself, ...
```

Write "Give tasks that arrive with a Local ID already in use a fresh one", not "sync.py: give a
fresh Local ID…". The project's own name (`Theme review:` in the Theme Review project), a
client, a tool, a workstream and a kind (`Question:`) are all prefixes. Where the tool or page
matters, put it inside the sentence. Group tasks with the project, a section, a tag, a field, a
dependency or a parent. See the 2026-11-25 addendum to ADR 022.

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
carries its own context, so name the page or section rather than leaning on the Asana
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
python3 studio/sync.py --update-task --task-gid {GID} \
  --task-notes "Corrected description."
```

## Notes

- Tasks are assigned to bainbot unless `--task-assignee` says otherwise - use `--task-assignee me` for a task Mark has to do, so it lands in his My Tasks
- The mirror entry will be overwritten on the next full sync with fresh data from Asana, but the task GID and local ID are preserved
- Use `--dry-run` to preview what would be created without hitting Asana
- To add subtasks under an existing task, see [new-subtask](new-subtask.md)
