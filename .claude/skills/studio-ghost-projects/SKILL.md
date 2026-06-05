---
name: studio-ghost-projects
description: Scan for inactive or ghost projects — registered projects with no recent Asana activity, stale mirrors, or abandoned branches. Surfaces projects that may need archiving, chasing, or closing.
allowed-tools: [Read, Bash]
---

# Studio Ghost Projects

Ghost projects are registered but going nowhere: no activity, no tasks moving, no contact in weeks. They clog the radar. Find them.

## Steps

### 1. Read the project registry

Read `/media/data/dev/bain-studio/studio/projects.json`. Each entry is `{"path": "...", "status": "..."}`. List all projects where status is `active` or `featured` — skip `paused` and `archived`.

### 2. Check last sync date

For each project, read its `.claude/asana-mirror.md`. Extract `Last synced:` date.

Flag any project where the mirror has not been synced in **14+ days**.

### 3. Check task activity

For each project mirror, scan for tasks:
- How many open tasks?
- What is the most recent `**Modified:**` date across all tasks?
- Are all tasks in DONE or SOMEDAY/MAYBE?

Flag any project where:
- All tasks are DONE or SOMEDAY/MAYBE (project may be complete but unclosed)
- No task has been modified in **30+ days**
- There are open tasks but none have a recent Progress note

### 4. Check for open branches

```bash
git -C {project_path} branch 2>/dev/null | grep -v "main\|master"
```

Flag any project with stale open branches (no commits in 14+ days).

### 5. Check last client contact

If `.claude/open-questions.md` exists, note any unanswered questions older than 14 days.

### 6. Report

Output a ghost projects report:

```
## Ghost Projects Scan — {YYYY-MM-DD}

### Active (no issues)
{list}

### Stale (no activity 14–30 days)
| Project | Last sync | Last task change | Open tasks | Status |
|---|---|---|---|---|

### Ghost (30+ days inactive)
| Project | Last sync | Last task change | Open tasks | Recommended action |
|---|---|---|---|---|

### Completed but unclosed
{projects where all tasks are DONE — may need harvest + closure}

### Recommended actions
{specific: archive X, chase Y, close Z}
```

**Recommended actions** should be specific. "Chase the client" is not an action. "Email Nicola — last contact was 2026-04-12, NORE-007 has been open since then" is.
