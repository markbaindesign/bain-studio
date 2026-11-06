---
name: open
description: "Open a project as a new window in the studio tmux session with Claude Code running."
argument-hint: "<PREFIX>"
allowed-tools: [Bash]
---

# Open Project Tab

Open a project as a window in the `studio` tmux session, with Claude Code running.

Usage: `/open PREFIX` — e.g. `/open MCF`, `/open NORE`, `/open UAP`

## Steps

### 1. Parse the prefix

The argument is a project prefix. Uppercase it. If no argument, list the known prefixes with `python3 /media/data/dev/bain-studio/studio/registry.py --list` and stop.

### 2. Look up the project path

Ask the resolver, which reads the registry outside the repo and falls back to
`docs/projects/` while that migration runs — see
`/media/data/dev/bain-studio/docs/utilities/registry.md`.

```bash
python3 /media/data/dev/bain-studio/studio/registry.py --prefix {PREFIX} --field path
```

A stem works: `KF` resolves `KF-WEB`. Two projects sharing a stem is ambiguous
and exits 1 rather than guessing, so pass the full prefix then.

If it exits non-zero, list the known prefixes with
`python3 /media/data/dev/bain-studio/studio/registry.py --list` and stop.

### 3. Open the tmux window

```bash
/media/data/dev/bain-studio/studio/scripts/studio-tmux open "{PREFIX}" "{PATH}" claude
```

This adds a `{PREFIX}` window to the studio session (reusing it if one is already open), selects
it, and switches to it when run from inside tmux. If the session does not exist yet, it is created
with the configured studio windows first. See `docs/utilities/studio-tmux.md`.

### 4. Confirm

Report: "Opened {PREFIX} → {PATH} in the studio tmux session." If the script printed
"Not inside tmux", add that Mark can attach with `studio-tmux`.
