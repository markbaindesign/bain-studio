---
name: asana-sync
description: Sync the assignee's Asana tasks to a local offline mirror. For the current project, runs the studio sync script to update .claude/asana-mirror.md, then reads and summarises the result. Use at the start of any work session or when asked to sync.
allowed-tools: [Read, Bash]
---

# Asana Sync Skill

Sync the current project's Asana tasks to its local mirror and summarise the result.

---

## Step 1 — Identify the current project

Read `CLAUDE.md` in the current working directory. Extract:
- `ASANA_TASK_PREFIX` — e.g. `MCF`
- `ASANA_PROJECT_GID` — confirm it's present
- `ASANA_PROJECT_NAME` — for the summary header

If `ASANA_PROJECT_GID` is not in `CLAUDE.md`, report: "No Asana project configured for this directory. Add ASANA_PROJECT_GID to CLAUDE.md to enable sync."

---

## Step 2 — Run the sync

```bash
python3 ~/dev/bain-studio/studio/sync.py --project {PREFIX}
```

This updates `.claude/asana-mirror.md` and `.claude/asana-ids.json` in the project root.

---

## Step 3 — Read the updated mirror

Read `.claude/asana-mirror.md`. Report:
- Total tasks assigned to the configured assignee
- New tasks since last sync
- Removed tasks (likely completed)
- Any overdue tasks
- Immediate priorities table

---

## Notes

- The sync script handles ID assignment, progress-note diffing, and posting changed notes to Asana as comments.
- Local IDs (e.g. MCF-001) are assigned sequentially and stored in `.claude/asana-ids.json`.
- Progress notes are preserved across syncs — only updated when meaningfully changed.
- To sync all studio projects at once: `python3 ~/dev/bain-studio/studio/sync.py`
- Sync log: `~/dev/bain-studio/studio/sync.log`
