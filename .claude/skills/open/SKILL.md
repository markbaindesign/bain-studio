---
name: open
description: Open a project in a new terminal tab with Claude Code. Takes a project prefix (e.g. /open MCF). Looks up the path from docs/projects/ and launches gnome-terminal in that directory.
allowed-tools: [Bash]
---

# Open Project Tab

Open a project in a new gnome-terminal tab with Claude Code running.

Usage: `/open PREFIX` — e.g. `/open MCF`, `/open NORE`, `/open PIPE`

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
    if pfx and pfx.group(1).upper() == prefix and path:
        print(path.group(1).strip())
        break
else:
    print("NOT_FOUND")
EOF
```

If `NOT_FOUND`, report "No project with prefix {PREFIX} found." and stop.

If the path does not exist on disk, report that and stop.

### 3. Open the terminal tab

```bash
gnome-terminal --tab --working-directory="{PATH}" -- zsh -c "claude; exec zsh"
```

### 4. Confirm

Report: "Opened {PREFIX} → {PATH} in a new tab."
