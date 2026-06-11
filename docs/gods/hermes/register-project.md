---
description: Registers a new project in the studio registry and sets up its Asana
  mirror
god: hermes
invoke: /register-project
tags:
- skill
---

# register-project

Registers an existing project directory in the studio system so it appears in Asana syncs and the morning startup report.

## Usage

```
/register-project <path> <PREFIX> "<name>"
```

**Example:**
```
/register-project /home/bain/code/vvv/clients/www/acme-corp ACME "Acme Corp"
```

## What it does

1. **Adds to `projects.json`** — appends `{"path": "{path}", "status": "active"}` if not already present. This is the registry `sync.py` reads to know which projects to sync.

2. **Adds to `CLAUDE.md` active projects table** — appends a row to the `## Active projects` table in the bain-studio `CLAUDE.md`, making it visible in the morning report.

## Output

```
register-project: Acme Corp
  ✓ added to projects.json
  ✓ added to CLAUDE.md active projects table (ACME)
```

## When to use

Run directly when:
- Adding a project that was created outside the `/commission` flow
- Re-registering a project that was manually removed from the registry
- Migrating an existing client project into the studio system

`/commission` calls this automatically as step 6.

## Related

- [`commission`](commission.md) — full setup flow that calls this
- [sync.md](sync.md) — the sync engine that reads `projects.json`
