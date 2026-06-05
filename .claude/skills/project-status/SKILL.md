---
name: project-status
description: Set or view project status in projects.json. Statuses: featured (terminal launch + top of standup), active (normal sync), paused (skip cron sync, manual only), archived (hidden, done). Args: [PREFIX] [featured|active|paused|archived]
allowed-tools: [Read, Edit, Bash]
---

# Project Status

Manage project lifecycle status in `studio/projects.json`.

Arguments: $ARGUMENTS
- No args → show current status of all projects
- One arg (prefix) → show status of that project
- Two args (prefix + status) → set status

Valid statuses: `featured`, `active`, `paused`, `archived`

---

## Show current statuses (no args or one arg)

Read `studio/projects.json`. For each entry print:

```
PREFIX  STATUS    name (path)
------  --------  -----------
MCF     active    Mhairi McFarlane (/home/bain/code/...)
NORE    paused    The Nature of Real Estate (...)
```

Derive prefix and name from each project's `CLAUDE.md` (`ASANA_TASK_PREFIX` and `ASANA_PROJECT_NAME`).

Sort order: featured → active → paused → archived.

---

## Set status (two args)

1. Read `studio/projects.json`
2. Migrate if still flat list of strings (convert to `{"path": "...", "status": "active"}`)
3. Find the entry whose project `CLAUDE.md` contains `ASANA_TASK_PREFIX: {PREFIX}`
4. If not found, list available prefixes and stop
5. Set `status` to the requested value
6. Write back to `studio/projects.json`

### Status-specific actions

**→ paused**
- Add a `paused_at` field with today's date (ISO format)
- Print: "NORE paused — will be skipped in cron sync. Run `python3 studio/sync.py --project NORE` to sync manually."

**→ archived**
- Confirm: "Archive NORE (The Nature of Real Estate)? This hides it from all reports. (y/n)"
- On confirm: set status, add `archived_at` date
- Print: "NORE archived."

**→ featured**
- Print: "NORE set to featured — will appear at top of standup and in terminal launcher."

**→ active**
- Remove `paused_at` / `archived_at` fields if present
- Print: "NORE reactivated."

---

## Notes

- `projects.json` is gitignored — changes are local only
- `featured` and `active` projects are synced by cron; `paused` and `archived` are skipped
- Paused projects can be manually synced with `python3 studio/sync.py --project {PREFIX}`
