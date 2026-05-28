# Bain Studio

Studio PM tooling for client project management.

## Sync script

- Run with `python3 studio/sync.py` (system `python` is 2.7)
- Projects registry: `studio/projects.json` (gitignored)
- Log: `studio/sync.log`
- Field setup (one-time, per project): `python3 studio/sync.py --setup --project {PREFIX}`
- All Asana API calls must use the **bainbot** account token (`ASANA_PAT` in `studio/.env`)

## Custom fields (workspace-level)

- Local ID: `ASANA_LOCAL_ID_FIELD_GID=1214878337481923`
- Last Synced: `ASANA_LAST_SYNCED_FIELD_GID=1214914270230951`

## Active projects

| Prefix | Name | Path |
|--------|------|------|
| MCF | Mhairi McFarlane | `/home/bain/code/misc/js/astrojs/client/mhairi_mcf` |
| PIPE | Upwork Pipeline | `/media/data/dev/misc/upwork-proposals` |
| NORE | The Nature of Real Estate | `/home/bain/code/vvv/clients/www/nore` |

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
