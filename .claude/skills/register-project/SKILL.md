---
name: register-project
description: Register a project in the bain-studio system — adds to projects.json, docs/projects/, the CLAUDE.md active projects table, and (if it has an Asana project) the Asana block in the project's own CLAUDE.md. Standalone step — callable directly or by /commission. Args: path prefix name
allowed-tools: [Read, Edit, Write, Bash, AskUserQuestion]
---

# Register Project

Add a project to the bain-studio registry so it appears in syncs and the startup report.

Arguments: $ARGUMENTS
- First arg: absolute path to the project
- Second arg: prefix (e.g. `GCOL`)
- Third arg: project name (quoted if multi-word)

If prefix or name are missing, ask the user rather than guessing — prefixes are permanent identifiers used in Asana task IDs and file names.

## Step 1 — Add to projects.json

Read `/media/data/dev/bain-studio/studio/projects.json`.
Each entry is an object: `{"path": "...", "status": "active"}`.
If the path is not already present, append `{"path": "{path}", "status": "active"}`.
Write the updated JSON back.

## Step 2 — Create docs/projects/{prefix}.md

This file (lowercase prefix, e.g. `docs/projects/tara.md`) is the single source of truth for project state per `bain-studio/CLAUDE.md` — the active-projects table there is just a path index. Look at an existing file in `docs/projects/` (e.g. `kf.md`) for the frontmatter shape and section layout, and write a new one following that pattern: prefix, name, status, client, type, repo, sector, stack, path, asana (yes/no), qa, inbox, open_tasks, current_focus, next_action, plus a short body (key contacts, notes).

## Step 3 — Add to CLAUDE.md active projects table

Read `/media/data/dev/bain-studio/CLAUDE.md`.

Find the `## Active projects` quick-reference table. Current format is path-only (name/status detail lives in the docs/projects file from Step 2):

```
| Prefix | Path |
|--------|------|
| MCF | `/home/...` |
```

Append a new row in that same format: `| {PREFIX} | \`{path}\` |`.

Write the updated CLAUDE.md back.

## Step 4 — Asana wiring

Ask the user (do not assume): does this project already have an Asana project, or does it need one created, or neither yet?

- **Already has an Asana project** (existing GID, not created via `sync.py --create`): this is the case most likely to be missed. `sync.py` reads Asana config from the *target project's own* `CLAUDE.md`, not from `docs/projects/`. Add this block to `{path}/CLAUDE.md`:

  ```
  ## Asana

  ASANA_PROJECT_GID: {gid}
  ASANA_TASK_PREFIX: {PREFIX}
  ASANA_PROJECT_NAME: {asana project name}
  ```

  Then run `/looper-onboard {PREFIX}` — it wires the shared Local ID/Last Synced custom fields, runs a real sync to confirm bainbot actually has access (not just asked-and-assumed) and to assign proper prefixed IDs to any existing tasks, and reports whether the project is genuinely ready to have tasks multi-homed into Studio Looper.

- **Needs a new Asana project**: don't create it yourself in this skill — point the user at `python3 studio/sync.py --create --name "{name}" --prefix "{PREFIX}" --path {path}` (documented in `bain-studio/CLAUDE.md` under "New project scaffold"). That command writes the `## Asana` block into the target `CLAUDE.md` for you as part of scaffolding.

- **No Asana yet**: leave `asana: "no"` in the docs/projects file and skip this step. Nothing to do in the target CLAUDE.md.

## Step 5 — Report

```
register-project: {name}
  ✓ added to projects.json
  ✓ created docs/projects/{prefix}.md
  ✓ added to CLAUDE.md active projects table ({PREFIX})
  ✓/… Asana: {what happened — wired existing GID / pointed to sync.py --create / none yet}
```
