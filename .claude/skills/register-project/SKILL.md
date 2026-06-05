---
name: register-project
description: Register a project in the bain-studio system — adds to projects.json and the CLAUDE.md active projects table. Standalone step — callable directly or by /commission. Args: path prefix name
allowed-tools: [Read, Edit, Bash]
---

# Register Project

Add a project to the bain-studio registry so it appears in syncs and the startup report.

Arguments: $ARGUMENTS
- First arg: absolute path to the project
- Second arg: prefix (e.g. `GCOL`)
- Third arg: project name (quoted if multi-word)

## Step 1 — Add to projects.json

Read `/media/data/dev/bain-studio/studio/projects.json`.
Append the path if it's not already present.
Write the updated JSON back.

## Step 2 — Add to CLAUDE.md active projects table

Read `/media/data/dev/bain-studio/CLAUDE.md`.

Find the `## Active projects` table. It looks like:

```
| Prefix | Name | Path |
|--------|------|------|
| MCF | Mhairi McFarlane | `/home/...` |
```

Append a new row:

```
| {PREFIX} | {name} | `{path}` |
```

Write the updated CLAUDE.md back.

## Step 3 — Report

```
register-project: {name}
  ✓ added to projects.json
  ✓ added to CLAUDE.md active projects table ({PREFIX})
```
