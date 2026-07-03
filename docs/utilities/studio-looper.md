---
tags: [skill, tool]
god: hermes
invoke: /studio-looper
description: Cross-project task queue — works BainBot tasks from any studio project in Asana drag order, handing completed work to Mark for review
---

# studio-looper

Cross-project task queue. BainBot works tasks from multiple Asana projects in the order Mark
sets in the Studio Looper Asana project. Completed work moves to Review — Mark approves before
marking done.

## Invoke

```bash
/studio-looper              # start the queue
/studio-looper --for 2h     # run for up to 2 hours
/studio-looper --use 10%    # consume at most 10% of quota
/studio-looper --yes        # skip queue confirmation
```

Must be invoked from `/media/data/dev/bain-studio`.

## How it works

1. Mark multi-homes tasks from any project (MCF, NORE, BSTD, PIPE…) into the **Studio Looper**
   Asana project, Queue section. Drag order = execution priority.
2. `/studio-looper` syncs the SL project, reads the Queue, and presents the list for
   confirmation before starting.
3. BainBot works each task in the correct project directory (derived from the task's prefix —
   MCF-007 → MCF project path, etc.).
4. On completion: task moves to **Review** section, reassigned to Mark. Task is NOT marked
   done in Asana.
5. On blocker: task moves to **Blocked** section, reassigned to Mark with a note.
6. Mark reviews tasks in the Review section, marks them done himself.

## Asana project sections

| Section | Meaning |
|---|---|
| Queue | Mark adds tasks here; drag = priority |
| In Progress | BainBot is currently working this |
| Blocked | Blocker found; assigned back to Mark |
| Review | Work done; Mark to review and close |
| Done | Mark confirmed; task complete |

## State file

`.claude/studio-looper.local.md` in the studio root. Written by the skill, read by the hook.
Queue entries are bare task IDs (`MCF-007`, `NORE-029`). The hook resolves project paths at
runtime via `studio/projects.json`.

## Stop hook

`~/.claude/hooks/studio-task-looper-stop-hook.sh` — fires on every session stop, reads the
state file, resolves the next task's project directory, and re-injects the prompt. Runs
alongside the per-project looper hook; only one fires per session (whichever state file exists).

## Local ID handling

Tasks multi-homed into Studio Looper keep their original project ID (e.g. MCF-007) via the
workspace-level Local ID custom field. sync.py's `PRESERVE_FOREIGN_IDS: true` flag in
`studio/looper/CLAUDE.md` prevents re-homing them to SL-NNN IDs.

## Setup (one-time)

1. Create "Studio Looper" project in Asana with sections: Queue, In Progress, Blocked, Review, Done
2. Add bainbot as a project member
3. Copy the project GID into `studio/looper/CLAUDE.md` (replace the placeholder)
4. `python3 studio/sync.py --setup --project SL`
5. Multi-home tasks into Queue and run `/studio-looper`

## Per-project looper

`/task-looper BSTD` (the original per-project looper) is unchanged. Use it for targeted
single-project runs. Studio Looper is for cross-project queues curated in Asana.

## Source files

- `studio/looper/CLAUDE.md` — project config (GID, prefix, preserve flag)
- `.claude/skills/studio-looper/SKILL.md` — skill definition
- `~/.claude/hooks/studio-task-looper-stop-hook.sh` — stop hook
- `studio/sync.py` — `preserve_foreign_ids` flag in ProjectConfig

## See also

- [task-looper](../gods/hermes/task-looper.md) — per-project version
- [Hermes](../gods/hermes/) — session orchestration
