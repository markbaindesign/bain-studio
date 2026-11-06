---
name: register-project
description: "Register a project in the studio: the registry outside this repo, a Dropbox project note, and the project's own Asana block."
argument-hint: "<path> <PREFIX> <name>"
allowed-tools: [Read, Edit, Write, Bash, AskUserQuestion]
---

# Register Project

Add a project to the bain-studio registry so it appears in syncs and the startup report.

Arguments: $ARGUMENTS
- First arg: absolute path to the project
- Second arg: prefix (e.g. `GCOL`)
- Third arg: project name (quoted if multi-word)

If prefix or name are missing, ask the user rather than guessing — prefixes are permanent identifiers used in Asana task IDs and file names.

## Step 1 — Add to the registry

**Identity never goes in this repo.** It is public. The registry is
`$XDG_DATA_HOME/bain-studio/registry.json` (default
`~/.local/share/bain-studio/registry.json`).

Add one entry, keyed by the lowercase slug:

```json
"tara": {
  "kind": "client",
  "prefix": "TARA",
  "name": "Project name",
  "client": "Client name, or Internal",
  "status": "active",
  "path": "/path/to/project",
  "repo": "git@...",
  "sector": "",
  "gid": "",
  "domains": ["live.example.com"],
  "ga4_property": "",
  "client_docs": "/media/data/Dropbox/Work/clients/{Client}/..."
}
```

`kind` must be `client` or `internal` — the commit guard reads it to decide
whose names to refuse, so an entry with the wrong `kind` either leaks a client
or blocks every commit naming an internal project.

**`domains` matters.** The guard cannot catch a client domain it was never told
about. If the project has a live site, a staging host or a provider install
name, record them here.

Then check it resolves:

```bash
python3 /media/data/dev/bain-studio/studio/registry.py --prefix {PREFIX}
```

Also append `{"path": "{path}", "status": "active"}` to
`/media/data/dev/bain-studio/studio/projects.json` (gitignored) while the
fallback still exists — see ADR 021's migration order.

## Step 2 — Write the project note in Dropbox

`$STUDIO_CONTENT_DIR/projects/{prefix}.md`, **not** in this repo. Copy the shape
of an existing note there. Frontmatter carries `tags: [studio-project]`, prefix,
name, status, client, type, repo, sector, stack, asana, qa, inbox,
current_focus, next_action — and **no path, GID, analytics property or client
docs folder**, which live in the registry. The body is prose: key contacts,
notes.

`projects.base` in that folder indexes these by their `studio-project` tag.

## Step 3 — Asana wiring

Ask the user (do not assume): does this project already have an Asana project, or does it need one created, or neither yet?

- **Already has an Asana project** (existing GID, not created via `sync.py --create`): this is the case most likely to be missed. Put the GID in the registry entry's `gid` — `sync.py` prefers the registry for every project. Then add this block to `{path}/CLAUDE.md` for the prefix and name, which the project's own tooling reads. **Omit `ASANA_PROJECT_GID` if `{path}` is inside the public bain-studio repo** (an internal tool, the looper): the registry already has it, and a tracked file must not.

  ```
  ## Asana

  ASANA_PROJECT_GID: {gid}
  ASANA_TASK_PREFIX: {PREFIX}
  ASANA_PROJECT_NAME: {asana project name}
  ```

  Then run `/looper-onboard {PREFIX}` — it wires the shared Local ID/Last Synced custom fields, runs a real sync to confirm bainbot actually has access (not just asked-and-assumed) and to assign proper prefixed IDs to any existing tasks, and reports whether the project is genuinely ready to have tasks multi-homed into Studio Looper.

- **Needs a new Asana project**: don't create it yourself in this skill — point the user at `python3 studio/sync.py --create --name "{name}" --prefix "{PREFIX}" --path {path}` (documented in `bain-studio/CLAUDE.md` under "New project scaffold"). That command writes the `## Asana` block into the target `CLAUDE.md` for you as part of scaffolding.

- **No Asana yet**: leave `asana: "no"` in the Dropbox project note, `gid: ""` in the registry, and skip this step. Nothing to do in the target CLAUDE.md.

## Step 4 — Report

```
register-project: {name}
  ✓ added to registry.json ({kind}, domains recorded)
  ✓ created $STUDIO_CONTENT_DIR/projects/{prefix}.md
  ✓/… Asana: {what happened — wired existing GID / pointed to sync.py --create / none yet}
```
