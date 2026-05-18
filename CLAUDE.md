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
