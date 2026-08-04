---
name: task-looper
description: DEPRECATED — superseded by studio-looper (ADR 009). Do not start a task-looper run; redirect to /studio-looper.
allowed-tools:
  - Read
---

# task-looper — DEPRECATED

This skill is retired. The studio has one looper: **studio-looper** (see ADR 009).

Do not run the old per-project loop. Instead:

1. Tell the user: "task-looper is deprecated — the studio looper now works all projects
   through the Studio Looper Asana queue."
2. If they want tasks worked, point them at the replacement:
   - Multi-home the task(s) into the **Studio Looper** Asana project and set
     **Looper Status: Queue** (tasks added with no status default to Queue on next sync).
   - Run `/studio-looper` (or let the nightly runner window pick them up:
     `studio/scripts/looper_runner.py`, cron 02:00).
3. Stop. Do not build a queue, write state files, or work any task from this skill.

Why it was retired, and what replaced each behaviour, is recorded in
`docs/adr/009-studio-looper-canonical.md`. Key differences to be aware of:

- Work happens on a local `looper/{run_id}` branch, **never pushed, never merged**
  (ADR 008's push-and-PR flow is superseded).
- Completed tasks go to **Looper Status: Review** for Mark — never marked done.
- Logging conventions from ADR 007 (`~/logs/task-looper.log`, sync.log format) are
  inherited unchanged by studio-looper.
