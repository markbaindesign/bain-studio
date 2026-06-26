---
name: create-repo
description: Create a new GitHub (public) or Bitbucket (private) repository. Wraps studio/scripts/create-repo. Usage: /create-repo <name> or /create-repo <name> --private
model: haiku
allowed-tools: [Bash]
---

# create-repo — Create a Repository

Runs `~/code/bain-studio/studio/scripts/create-repo` (or the equivalent path under `/media/data/dev/bain-studio/studio/scripts/create-repo`) to create a new repo on GitHub or Bitbucket.

- `--public` (default) → creates on GitHub as a public repo
- `--private` → creates on Bitbucket as a private repo

## Steps

### 1. Parse the invocation

Extract from the user's command:
- Repo name (required)
- `--public` or `--private` flag (default: `--public`)
- `--desc TEXT` if provided
- `--clone PATH` if they want it cloned locally

### 2. Confirm with the user

Echo a one-line summary before running:
```
Creating {public GitHub / private Bitbucket} repo: {name}
```

If `--clone PATH` was given, note where it will be cloned.

### 3. Run the script

```bash
/media/data/dev/bain-studio/studio/scripts/create-repo {name} [--public|--private] [--desc "..."] [--clone PATH]
```

If the script exits non-zero, show the error and stop.

### 4. Report the result

Show the remote URL. If the repo was cloned, show the path. If a remote was added to the current repo, confirm it.

If Bitbucket credentials are not configured, the script will prompt interactively — let it run.
