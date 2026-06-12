---
tags: [skill]
god: hermes
invoke: /bd-task-looper
description: Self-driving task queue — works BainBot-assigned tasks one at a time, driven by a stop hook, until the queue is empty
---

# bd-task-looper

Runs BainBot-assigned tasks autonomously, one at a time. Reads the Asana mirror, builds a prioritised queue, works the first task, outputs a completion promise, and the stop hook advances the queue automatically.

## Usage

```
/bd-task-looper
/bd-task-looper <note>
```

The optional note is context for the current run (e.g. a specific task to prioritise, or a constraint to observe).

## How it works

1. Syncs from Asana to get the latest task state
2. Builds a queue of all tasks where `Assignee: BainBot` and `Section ≠ DONE`, ordered by due date then dependency readiness
3. Writes `.claude/bd-task-looper.local.md` with the queue state
4. Works the first task (code tasks get a feature branch; non-code tasks do not touch git)
5. Outputs `<promise>{ID}_COMPLETE</promise>` or `<promise>{ID}_BLOCKED</promise>`
6. Stop hook advances the queue and re-injects the next task automatically

## Completion vs blocked

- **Complete:** problem solved, change works, nothing newly broken. Mirror updated to DONE, sync run, PR raised if code was written.
- **Blocked:** needs Mark's input, external dependency, or task is ambiguous. Blocker task created in Asana, assigned to Mark, linked as a dependency of the blocked task.

## State file

`.claude/bd-task-looper.local.md` — written at queue start, deleted when the queue empties. Gitignored.

## Guard rails

- Never merges PRs — all PRs are for Mark's review
- Never commits to main/master
- Never creates a branch for non-code tasks (research, audits, config, sync)
- Never touches tasks assigned to Mark
- Ambiguous = blocked, not guessed-at
