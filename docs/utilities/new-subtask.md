---
tags: [utility, asana, tasks, workflow]
god: hermes
command: python3 studio/sync.py --create-subtask
description: Create one or more subtasks under an existing Asana task from the CLI, in the order given, via bainbot. Subtasks stay out of the local mirror.
---

# New Subtask

Adds subtasks under an existing Asana task via bainbot. Sibling of [new-task](new-task.md), which creates
top-level tasks.

## Usage

```bash
python3 /media/data/dev/bain-studio/studio/sync.py \
  --create-subtask \
  --task-gid 1217094791482756 \
  --subtask-name "Audit redirects" \
  --subtask-name "Fix the ones that 404" \
  --subtask-name "Re-crawl and confirm"
```

The GIDs of the new subtasks are printed to stdout, one per line, in the order the names were given.

## Options

```
--create-subtask       Switch into this mode
--task-gid GID         Parent task GID (required). It is the "Asana ID" field of the task in
                       the project's asana-mirror.md
--subtask-name NAME    Subtask title (required, repeatable). Created in the order given
--dry-run              Log what would be created without calling Asana; prints placeholder GIDs
```

Leaving out `--task-gid` or every `--subtask-name` is a usage error (exit code 2) and nothing is created.

## Behaviour

- One API call per subtask, so a failure part-way leaves the earlier subtasks created. Nothing is
  rolled back.
- Subtasks are **not added to any project**, so they do not appear in the local mirror and get no
  local ID (unlike `--create-task`).
- Only a title is set. There is no notes, due date or assignee option.
- Uses the bainbot token like every other sync.py write.

## Tests

`studio/tests/test_sync.py` covers the ordering and payload of the calls, `--dry-run`, an empty name
list, and both usage errors.
