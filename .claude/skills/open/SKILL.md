---
name: open
description: Open a project as a new window in the studio tmux session, with Claude Code running. Takes a project prefix (e.g. /open MCF). Looks up the path from docs/projects/ and opens the window via studio-tmux.
allowed-tools: [Bash]
---

# Open Project Tab

Open a project as a window in the `studio` tmux session, with Claude Code running.

Usage: `/open PREFIX` — e.g. `/open MCF`, `/open NORE`, `/open UAP`

## Steps

### 1. Parse the prefix

The argument is a project prefix. Uppercase it. If no argument, list available prefixes from `docs/projects/` and stop.

### 2. Look up the project path

Read the frontmatter from each file in `/media/data/dev/bain-studio/docs/projects/*.md` and find the one where `prefix:` matches. Extract the `path:` value.

```bash
python3 - <<'EOF'
import os, re

projects_dir = "/media/data/dev/bain-studio/docs/projects"
prefix = "PREFIX_PLACEHOLDER"

for fname in os.listdir(projects_dir):
    if not fname.endswith('.md'):
        continue
    content = open(os.path.join(projects_dir, fname)).read()
    fm = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not fm:
        continue
    pfx = re.search(r'^prefix:\s*(\S+)', fm.group(1), re.MULTILINE)
    path = re.search(r'^path:\s*(.+)', fm.group(1), re.MULTILINE)
    if pfx and path:
        p = pfx.group(1).upper()
        if p == prefix or p.startswith(prefix + '-'):
            print(path.group(1).strip())
            break
else:
    print("NOT_FOUND")
EOF
```

If `NOT_FOUND`, report "No project with prefix {PREFIX} found." and stop.

If the path does not exist on disk, report that and stop.

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
