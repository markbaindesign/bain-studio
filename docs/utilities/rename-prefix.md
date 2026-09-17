---
tags: [utility, asana, sync]
command: python3 studio/scripts/rename_prefix.py OLD NEW [--apply]
description: Rename a project's Asana task ID prefix while keeping every task's number (PIPE-063 → UAP-063)
---

# rename-prefix

Renames a project's task ID prefix without scrambling its IDs.

```bash
python3 studio/scripts/rename_prefix.py PIPE UAP           # dry run: lists every change
python3 studio/scripts/rename_prefix.py PIPE UAP --apply
```

## Why not just edit CLAUDE.md

sync.py treats any Local ID that doesn't start with the project's prefix as a task re-homed from
another project, and gives it a **new** sequence number. Change `ASANA_TASK_PREFIX` alone and the
next sync turns PIPE-063 into something like UAP-068, for every task.

## What it does

1. Refuses to start while a `sync.py` process is running (there is no sync lock; cron runs hourly
   on the hour from the ops worktree, and syncs also run ad hoc).
2. Rewrites the Local ID custom field in Asana for every task in the project holding `OLD-NNN`,
   including long-completed tasks the normal sync never fetches. If any write fails it stops
   before touching local files; re-running skips tasks already renamed.
3. Rewrites `OLD-NNN` in every registered project's `asana-ids.json` (Studio Looper holds foreign
   IDs too).
4. Rewrites task headings and `Local ID:` lines in every registered mirror. Notes, progress and
   blockers are left alone so the next sync has nothing spurious to push.
5. Switches `ASANA_TASK_PREFIX` in the project's CLAUDE.md.

Run it well clear of the top of the hour: 62 Asana writes took about two minutes.

## Afterwards, by hand

- Verify: `python3 studio/sync.py --project NEW --dry-run` should report no re-homed or newly
  assigned IDs.
- Update references in docs and code: `docs/projects/{old}.md` (rename the file and its
  `prefix:`), the Active projects table in `CLAUDE.md`, `docs/studio-map.md`, skills and
  collectors that pass `--project OLD`. Leave history (changelogs, commit messages, old analyses)
  as it is.
- The Asana project's own name is not changed.

## History

- 2026-09-17: PIPE → UAP (Upwork Pipeline).
