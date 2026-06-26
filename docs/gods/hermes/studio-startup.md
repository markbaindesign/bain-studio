---
description: Morning routine — syncs all mirrors, runs Abderus sweep, delivers a pulse
  report
god: hermes
invoke: /studio-startup
tags:
- skill
---

# Studio Startup

Morning routine. Syncs all project mirrors, runs Abderus, surfaces what matters today. Run at the start of every work session.

## Invoke

```
/studio-startup
```

## What it does

1. **Sync all project mirrors** — runs `python3 studio/sync.py` to pull the latest Asana state for all registered projects
2. **Read the studio pulse** — reads `studio/projects.md` and each active project's `.claude/asana-mirror.md`, extracting overdue tasks and open questions
3. **Run Abderus** — invokes `/abderus` to surface harvest gaps, stale projects, and overdue obligations
4. **Report** — outputs a combined startup report: overdue tasks by project, Abderus findings, anything needing immediate attention

## Output

A startup report covering:
- Overdue tasks (due date in the past, by project)
- Tasks with no Progress note
- Open questions from `.claude/open-questions.md` per project
- Abderus timing sweep findings (harvest gaps, follow-ups due, stale triage entries)

## Notes

- Always run this before starting any client work — it ensures the mirrors are fresh and nothing is slipping
- If any project fails to sync, Abderus still runs against the stale mirror; the failure is noted in the report
- Pairs with `/studio-shutdown` which closes the session loop

## See also

- [abderus.md](abderus.md) — the timing sweep invoked at step 3
- [sync.md](sync.md) — the underlying Asana sync used at step 1
