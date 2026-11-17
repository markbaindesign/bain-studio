---
tags: [tool, asana, planning]
god: hermes
invoke: studio/critical_path.py
command: python3 studio/critical_path.py --project PREFIX [--dry-run]
description: Works out a project's critical path from its Asana dates and dependencies and marks it in a shared "Critical Path" field, so the Gantt can be coloured by it
---

# critical-path

Asana's own "highlight critical path" switch is not available on the studio's plan. This
script computes the path itself and writes it to a shared single-select field,
**Critical Path** (one value, *Critical*). In the Gantt or Timeline view, set
**Options → Color tasks by → Critical Path**.

```bash
python3 studio/critical_path.py --project PSK --dry-run   # print the path, write nothing
python3 studio/critical_path.py --project PSK             # write the field
```

The first real run creates the field in the workspace library if it does not exist and
attaches it to the project. Put its GID in `studio/.env` as
`ASANA_CRITICAL_PATH_FIELD_GID` to skip the lookup.

## How the path is worked out

- **Target:** the open milestone with the latest due date.
- **Items:** open tasks and milestones with a due date that lead to the target through
  "blocked by" links. Completed and undated items are left out.
- **Durations:** working days (Mon–Fri) from start to due; one day with no start date. A
  milestone occupies its own day, and a blocker must finish the working day before the
  item it blocks, as Asana's finish-to-start rule requires.
- **Slack:** a backward pass from the target gives each item's latest finish; slack is the
  working days between its due date and that.
- **The path:** from the target, back through the blocker with the least slack at each step,
  plus anything with no slack. A plan with buffer between milestones has almost no
  zero-slack work, so this marks the chain that runs out of room first.

The output lists each item on the path with its slack. Negative slack is a scheduling
conflict: the item is due after the latest day it could finish.

## What it needs from the project

The path is only as good as the links. Each task should block the milestone it leads to,
and be blocked by the milestone before it, wherever its dates allow. A task with dates but
no links is invisible to the calculation. A dependency cycle stops the run with the names
of the items in the loop.

Holidays are not modelled.

## Limits

- Runs by hand per project. Running it on every sync, for build projects only, is part of
  BSTD-887.
