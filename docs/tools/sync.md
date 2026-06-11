# sync.py — Asana Sync

Bidirectional sync between local project mirrors and Asana. Each project's tasks are mirrored to `{project}/.claude/asana-mirror.md`.

## Usage

```bash
cd ~/code/bain-studio

python3 studio/sync.py                          # sync all active projects
python3 studio/sync.py --project ACME           # sync one project by prefix
python3 studio/sync.py --dry-run                # preview changes without writing
python3 studio/sync.py --create \               # scaffold a new Asana project
    --name "Acme Corp" \
    --prefix ACME \
    --path /home/bain/code/vvv/clients/www/acme-corp \
    --yes
```

## Conflict resolution

- **Asana modified more recently than mirror** → Asana wins, mirror is updated
- **Mirror modified more recently** → mirror wins, changes are pushed to Asana

## Projects registry

`studio/projects.json` lists which projects to sync:

```json
[
  {"path": "/home/bain/code/vvv/clients/www/acme-corp", "status": "active"}
]
```

This file is gitignored — copy from `projects.example.json` on a new machine. Use `/register-project` to add entries rather than editing directly.

## Required environment variables

Set in `studio/.env` (gitignored):

| Variable | Description |
|---|---|
| `ASANA_PAT` | Personal access token |
| `ASANA_WORKSPACE_GID` | Workspace GID |
| `ASANA_BAINBOT_GID` | GID of the Asana bot user |
| `ASANA_LOCAL_ID_FIELD_GID` | GID of the custom text field for local IDs |
| `ASANA_TEMPLATE_PROJECT_GID` | Template project to duplicate when creating new projects |

## Log

`studio/sync.log` — rotating, 5 MB × 3 files.

## In the studio workflow

`sync.py` is run automatically by the `/studio-startup` and `/studio-shutdown` skills, and by the Hermes agent on a schedule. Run it manually when you need a fresh mirror before starting work on a project.

## Related

- [`register-project`](register-project.md) — add a project to the registry
- [`commission`](commission.md) — uses `sync.py --create` to scaffold new Asana projects
