---
name: focus
description: "Mid-day project context switch from the bain-studio directory: looks up the project path and gives a full /recap brief."
argument-hint: "<PREFIX>"
allowed-tools: [Read, Bash]
---

# Focus

Switch focus to a project mid-day. Run from `/media/data/dev/bain-studio` with a prefix argument.

Usage: `/focus MCF` or `/focus NORE`

## Steps

### 1. Parse the argument

The argument is a project prefix (e.g. `MCF`, `NORE`, `WTF`). If no argument provided, list active projects and ask which one.

### 2. Look up the project path

Ask the resolver. It reads the registry outside the repo and falls back to
`docs/projects/` while that migration runs — see `/media/data/dev/bain-studio/docs/utilities/registry.md`.

```bash
python3 /media/data/dev/bain-studio/studio/registry.py --prefix {PREFIX} --field path
```

It exits 1 and prints nothing on stdout for an unknown prefix. `{PREFIX}` may be a
stem: `KF` resolves `KF-WEB`.

If it exits non-zero, list the known prefixes with `python3 /media/data/dev/bain-studio/studio/registry.py --list` and abort.

### 3. Run recap for that project

Change to the project directory and run the same steps as `/recap`:

1. Git context — branch, last 3 commits, dirty flag
2. Asana state — read `{path}/asana-mirror.md`
3. Inbox — check `{path}/.claude/inbox/` for unread messages
4. Open questions — read `{path}/.claude/open-questions.md`
5. Synthesise next action

### 4. Output

Same format as `/recap`:

```
## Recap — {PROJECT_NAME} — {YYYY-MM-DD HH:MM}

### Git
Branch: {branch} {[DIRTY] if uncommitted changes}
Recent: {last 3 commits, one per line}

### In progress
{list or "None"}

### Blocked
{list or "None"}

### Inbox
{list or "Clear"}

### Open questions
{list or "None"}

### Next action
→ {synthesised suggestion}
```
