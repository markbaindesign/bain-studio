---
tags: [utility, registry, pmbot]
god: periphetes
command: python3 studio/scripts/gen-projects-index.py
description: Regenerates the table in PmBot's projects index from the studio registry, so the index PmBot reads at session start cannot drift from the registry.
---

# gen-projects-index

PmBot reads `$STUDIO_CONTENT_DIR/projects-index.md` at the start of every session. It was
written by hand, which makes it one more copy of project identity, the drift
[ADR 021](../adr/021-studio-state-and-registry-leave-the-repo.md) exists to end. This
script regenerates its table from `registry.json`.

```bash
python3 studio/scripts/gen-projects-index.py              # preview on stdout
python3 studio/scripts/gen-projects-index.py --write      # rewrite the index
python3 studio/scripts/gen-projects-index.py --no-asana   # skip the Asana lookup
```

Run `--write` after `/register-project`, or after a project's status changes in the registry.

## What it generates and what it keeps

Only the table is generated. The intro, "Shared locations" and "Adding a project" sections
are prose that a human owns, and they are carried over from the existing file word for word.
A comment above the table says it is generated.

Only `status: active` entries are listed. Paused, inactive and archived projects are left out.

| Column | Source |
|---|---|
| Prefix | registry `prefix` |
| Project | registry `name` |
| Asana project | Asana project name, a read-only lookup with the bainbot PAT |
| Asana GID | registry `gid` |
| Dropbox folder | registry `dropbox`, else `client_docs`, else `none` |
| Missions folder | `missions/` if that folder exists inside the Dropbox folder, else `none` |
| Agent | registry `agent`, else `DevBot` |

Nothing is guessed. A missing value prints `none`, a registered Dropbox folder that no longer
exists prints `(missing)`, and an Asana name the script could not fetch prints `(not fetched)`.

## Optional registry fields

The registry needs two optional fields so that it can fill every column:

- `dropbox`: the project's Dropbox folder, for projects whose folder is not `client_docs`.
  Internal projects have no `client_docs`, so without this field they show `none`.
- `agent`: only for a project that is not handled by DevBot.

## Configuration

| Input | Default | Override |
|---|---|---|
| Registry | `$XDG_DATA_HOME/bain-studio/registry.json` | `BAIN_REGISTRY` |
| Index file | `$STUDIO_CONTENT_DIR/projects-index.md` | `BAIN_PROJECTS_INDEX` |
| `.env` (`ASANA_PAT`, `STUDIO_CONTENT_DIR`) | `studio/.env`, then `~/.config/bain-studio/.env` | `BAIN_STUDIO_ENV` |

If the registry is missing, the script exits with code 2 and does not build anything.
It never builds the index from the `docs/projects` fallback.
