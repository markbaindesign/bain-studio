# Offline Asana Mirror — Design Notes

## The problem

The official approach to giving Claude access to Asana is an MCP server: Claude calls Asana at runtime, reads tasks, writes back. This works, but it has a structural weakness for ongoing project work.

Every session starts cold. To know what's on your plate you either ask Claude to fetch it (a conscious, manual step) or wire up a CLAUDE.md that tells Claude to do so automatically — but that still costs a live API call at context load time, and the result isn't visible to you until Claude surfaces it.

For a small studio managing a handful of active projects, what you actually want is: open a project, and Claude already knows the current state of your tasks — no MCP call needed, no "let me check Asana first."

## The pattern

Pull Asana tasks on a schedule into a local markdown file (`asana-mirror.md`) that lives in the project's `.claude/` directory. Because Claude Code loads all files in `.claude/` into context at session start, the task state is just *there* — readable by Claude and by the user without any tool invocation.

```
studio/sync.py          # runs on demand or via cron
  └── writes to
      <project>/.claude/asana-mirror.md   # loaded automatically into Claude context
```

The sync script is the only part that talks to Asana. Everything Claude does at session time is read from the local file.

## Why not just MCP live?

| | Live MCP | Offline mirror |
|--|----------|----------------|
| Task state in context at session start | No (requires tool call) | Yes |
| Works without internet | No | Yes |
| Reflects edits made outside Claude | Immediately | On next sync |
| Claude can edit tasks directly | Yes | Via mirror edits + sync writes back |
| Adds latency to session start | Yes | No |

For fast-moving work (multiple Claude sessions per day, frequent Asana updates), live MCP wins on freshness. For studio work (one or two sessions per project per week, tasks that don't change minute-to-minute), the offline mirror wins on convenience.

## The mirror format

`asana-mirror.md` is structured markdown, not a flat dump. Each task gets a consistent block:

```markdown
### MCF-004 — Write case study for Penguin deal

- **Local ID:** MCF-004
- **Asana ID:** 1234567890
- **Section:** In Progress
- **Due:** 2026-05-30
- **Notes:** First draft by end of week…
- **Blockers:** None identified.
- **Progress:** Checked 2026-05-20.
- **Modified:** 2026-05-19T14:22:00
- **URL:** https://app.asana.com/0/…
```

This format was chosen because:
- Claude can parse it reliably with a regex (used for carrying forward `Blockers` and `Progress` across syncs)
- It's human-readable without tooling
- The `Progress` field gives Claude a place to write status updates that aren't just "checked"
- `Blockers` persists across syncs without being overwritten by Asana data

## Local IDs

Asana GIDs are 16-digit numbers. They're stable but not human-memorable. The sync script assigns short prefixed IDs (`MCF-001`, `MCF-002`, …) the first time it sees each task, writes them to a workspace-level custom text field in Asana ("Local ID"), and stores the mapping in `.claude/asana-ids.json`.

This means:
- Claude can reference tasks by a short, memorable ID
- The ID appears in Asana's task detail view (useful when switching to the Asana UI)
- The mapping survives mirror rebuilds — IDs are stable across syncs

## Bidirectional sync

The mirror isn't purely a read cache. Two things write back to Asana:

**Section moves.** If the mirror's `Section` field differs from Asana and the mirror is newer than the last Asana modification, Claude's edit wins — the sync script moves the task in Asana. If Asana is newer, Asana wins. This lets Claude drag tasks between sections (Backlog → In Progress → DONE) and have that propagate.

**Progress comments.** If the `Progress` field contains anything other than a plain `Checked YYYY-MM-DD.` timestamp, the sync posts it as a comment on the Asana task. This surfaces Claude's working notes in Asana's activity log without requiring a separate step.

## Project discovery

The sync script reads `studio/projects.json` (a list of absolute paths, gitignored) and loads Asana config from each project's `CLAUDE.md`:

```
ASANA_PROJECT_GID: 1234567890123456
ASANA_TASK_PREFIX: MCF
ASANA_PROJECT_NAME: Mhairi McFarlane
```

Config lives in CLAUDE.md rather than a separate config file so there's one canonical source of truth per project, and new projects wire up with a single field addition.

## Setup vs sync

Two operating modes:

- `--setup` — one-time per project. Creates and attaches the "Local ID" and "Last Synced" custom fields in Asana, writes their GIDs to `asana-ids.json`. Never needed again.
- Normal run — fetches tasks, assigns IDs, builds mirror, stamps Last Synced, posts progress comments, syncs section moves.

## What the sync does not do

- Create or delete tasks (Claude's live MCP tools handle that)
- Sync tasks assigned to other users
- Handle subtasks
- Sync attachments or dependencies

The mirror is focused on giving the assignee a clear picture of their open work. Full Asana management is better done through the live MCP or the Asana UI.

## Auth

All Asana API calls use a dedicated service account token (`bainbot`), not the human account. This keeps API rate limits and audit logs clean, and means the human account's OAuth state doesn't affect syncs running on a schedule.

## Running on a schedule

```bash
# cron: sync all projects at 8am and 2pm
0 8,14 * * * cd /media/data/dev/bain-studio && python3 studio/sync.py >> studio/sync.log 2>&1
```

The rotating log (`sync.log`, 5 MB × 3) means you can diagnose failures without the log growing unbounded.
