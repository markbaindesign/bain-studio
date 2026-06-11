# Bain Studio

Studio PM tooling for client project management.

## Git workflow

- Always work on `develop`. Never commit directly to `main`.
- Feature branches off `develop` via `git flow feature start {name}`.
- Merge `develop` → `main` only when releasing.

## Sync script

- Run with `python3 studio/sync.py` (system `python` is 2.7)
- Projects registry: `studio/projects.json` (gitignored)
- Log: `studio/sync.log`
- Field setup (one-time, per project): `python3 studio/sync.py --setup --project {PREFIX}`
- All Asana API calls must use the **bainbot** account token (`ASANA_PAT` in `studio/.env`)
- sync.py **pulls** from Asana only — edits to the mirror push back; new tasks must be created via API before they appear
- Asana duplication is async — `_wait_for_job` polls up to 300s

## New project scaffold

```
python3 studio/sync.py --create --name "Client Name" --prefix "CLN" --path /path/to/project
```

- Duplicates `ASANA_TEMPLATE_PROJECT_GID` from `studio/.env`, clears placeholder tasks, adds Mark + bainbot as members
- Optional: `--template GID`, `--members GID,GID`, `--yes` (skip confirmation gate)
- Custom project icons are **UI-only** — set manually in Asana after `--create`
- `ASANA_USER_GID` (Mark's GID) and `ASANA_TEMPLATE_PROJECT_GID` must be set in `studio/.env`

## Content locations

Studio output (specs, finance, pipeline, portfolio, briefs) lives in Dropbox, not this repo:

- **Root:** `~/Dropbox/Studio/context/` (set via `STUDIO_CONTENT_DIR` in `studio/.env`)
- Case studies: `$STUDIO_CONTENT_DIR/portfolio/{project-slug}/`
- Internal briefs: `$STUDIO_CONTENT_DIR/internal/`
- Specs nursery: `$STUDIO_CONTENT_DIR/specs/`
- Finance: `$STUDIO_CONTENT_DIR/finance/`

`context/` is gitignored — all content is Dropbox-synced only.

## Custom fields (workspace-level)

- Local ID: `ASANA_LOCAL_ID_FIELD_GID=1214878337481923`
- Last Synced: `ASANA_LAST_SYNCED_FIELD_GID=1214914270230951`

## Active projects

| Prefix | Name | Path |
|--------|------|------|
| MCF | Mhairi McFarlane | `/home/bain/code/misc/js/astrojs/client/mhairi_mcf` |
| PIPE | Upwork Pipeline | `/media/data/dev/misc/upwork-proposals` |
| DOM | Premium Domains | `/media/data/dev/misc/premium_domains` |
| NORE | The Nature of Real Estate | `/home/bain/code/vvv/clients/www/nore` |

## Skills

Skills created while working in this project live in `.claude/skills/` at the project root, not in `~/.claude/skills/` (global). This keeps studio tooling versioned and committed with the repo.

**Studio skills available globally** — symlinked from this repo into `~/.claude/skills/` so they work in any project context:

```bash
ln -s /media/data/dev/bain-studio/.claude/skills/{name} ~/.claude/skills/{name}
```

| Skill | Reason |
|-------|--------|
| `brand-doc` | brands any .md file as a Bain Design PDF |

**Global-only skills** (not in this repo — live directly in `~/.claude/skills/`):
- `grill-me` — general planning, useful everywhere
- `web-researcher` — general research
- `wp-css-override` — used in client WordPress projects
- `wp-plugin-expert` — used in client WordPress projects
- `copywriter` — used for client copy

## Project inboxes

Each project can receive messages from other agents via `.claude/inbox/`. Run `/check-inbox` at the start of any session to process pending messages. Messages are written by `studio/postman.py` and archived to `.claude/inbox/processed/` once read.

## Asana access rule

The PM agent must **never use Asana MCP tools** to make changes (the MCP uses your human OAuth account). All Asana mutations go through `sync.py`, which uses the bainbot PAT. The Asana MCP is disabled for this project via `disabledMcpjsonServers` in `.claude/settings.json`.

The PM workflow is:
1. Read task state from local mirror files (e.g. `PROJ-123.md`)
2. Edit mirrors if changes are needed
3. Run `python3 studio/sync.py` to push changes to Asana via bainbot

## Asana

ASANA_PROJECT_GID: 1215208851588912
ASANA_TASK_PREFIX: BSTD
ASANA_PROJECT_NAME: Bain Studio

## Definition of done

Nothing is considered built until the docs are written. Every tool, skill, or agent that ships must have a corresponding note in `docs/` under its god's folder (or `docs/utilities/` for shared utilities). The note must include frontmatter (`tags`, `god`, `invoke`/`command`, `description`) so it appears in the Obsidian bases indexes.
