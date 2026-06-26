---
description: Creates and initialises a new project directory as a git repo
god: hephaestus
invoke: /scaffold-dir
tags:
- skill
---

# scaffold-dir

Creates a new project directory, initialises git, and wires up studio tooling. It's a standalone step but is also called by `/commission` as part of the full project setup flow.

## Usage

```
/scaffold-dir <path> [name]
```

- `path` — absolute path for the new project directory
- `name` — optional display name, used in the initial commit message. Defaults to the directory basename.

**Example:**
```
/scaffold-dir /home/bain/code/vvv/clients/www/acme-corp "Acme Corp"
```

## What it does

1. **Validates** — aborts if the path is non-empty, or if the parent directory doesn't exist
2. **Creates** `{path}/`
3. **Git init**
4. **Writes** a minimal `.gitignore` (`.env`, `node_modules/`, `__pycache__/`, etc.)
5. **Initial commit** — `init: scaffold {name}`
6. **Creates a Shutter profile** — `shutter-profile create "{name}" "{path}/qa/qa-inbox"`, also creating the `qa/qa-inbox` directory. Skipped silently if `shutter-profile` is not on PATH.

## Output

```
scaffold-dir: /home/bain/code/vvv/clients/www/acme-corp
  ✓ directory created
  ✓ git init
  ✓ .gitignore written
  ✓ initial commit
  ✓ shutter profile 'Acme Corp' created
```

## Shutter profile

The created profile points Shutter's save folder to `{path}/qa/qa-inbox` — screenshots land directly in the project's QA inbox. Launch Shutter for the project with:

```bash
shutter --profile='Acme Corp'
```

See [shutter.md](shutter.md) for full Shutter documentation.

## In the commission flow

`scaffold-dir` is step 2 of `/commission`, which also handles Asana project creation, studio registration, CLAUDE.md generation, and task seeding. Run `scaffold-dir` directly only when you need the directory without the full commission ceremony — e.g. internal tools, experiments, or projects not tracked in Asana.

## Related

- [`/commission`](commission.md) — full project setup including Asana and studio registration
- [`/register-project`](register-project.md) — add an existing directory to the studio registry
- [shutter.md](shutter.md) — Shutter profile management
