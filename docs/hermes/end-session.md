---
tags: [skill, session, workflow, git]
god: hermes
invoke: /end-session
description: Wrap up the current project session. Commits changes, syncs the mirror for this project only, writes a handoff note to pm-log.md. Run when switching context or finishing a topic.
---

# End Session

Wraps up the current project session cleanly. Scoped to the project in the current working directory.

## When to use

- Switching from one project to another mid-day
- Finishing a focused topic (e.g. done with the Cloudways research, moving to NORE)
- Quick wrap-up without a full end-of-day retro

Use `/studio-shutdown` instead for end-of-day (syncs all projects, runs a full retro).

## What it does

1. Summarises what happened this session
2. Commits any uncommitted changes in the current project
3. Updates `Progress:` notes in the mirror for tasks that were touched
4. Syncs the mirror to Asana for this project only
5. Appends a handoff note to `.claude/pm-log.md` in the current project
6. Outputs an end-session report

## Output

```
## End Session — {PROJECT_NAME} — {YYYY-MM-DD HH:MM}

### Committed
{commit hash + message, or "Working tree was clean"}

### Mirror
{which tasks were updated}

### Sync
{synced OK / failed}

### Handoff
Done:
- ...
Next action: ...
Blockers: ...
```

## Handoff log

Session notes accumulate in each project's own `.claude/pm-log.md`. Useful for:
- Re-entry context when `/recap` isn't enough
- Understanding what happened across sessions in that project without reading git log

For a cross-project overview, read each project's `.claude/pm-log.md` in turn (or build a skill that does this).
