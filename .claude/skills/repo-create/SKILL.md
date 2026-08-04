---
name: repo-create
description: Create a GitHub or Bitbucket repository and wire up the local git repo (init, remote, push, default branch). Provider-agnostic - defaults to Bitbucket private, GitHub for --public. Wraps studio/scripts/repo-create. Usage: /repo-create [name] [--gh|--bb] [--public]
model: haiku
allowed-tools: [Bash]
---

# repo-create — Create a Repository (any provider)

Runs `/media/data/dev/bain-studio/studio/scripts/repo-create` to create a repo on
GitHub or Bitbucket and connect the current directory's git repo to it: creates the
repo, git-inits if needed, sets the remote, pushes, and (Bitbucket) sets the default
branch to match.

Provider defaults: **private → Bitbucket, `--public` → GitHub.** Force with `--gh` / `--bb`.

## Usage

```
/repo-create                          # Bitbucket private repo named after cwd
/repo-create my-tool --public         # GitHub public repo
/repo-create my-repo --gh --private   # GitHub private repo
/repo-create --name kf-x --workspace markbaindesign --branch main
/repo-create my-repo --no-push        # create only, no local wiring
/repo-create my-repo --clone ~/code/my-repo
```

## Steps

### 1. Parse the invocation

Extract repo name (default: cwd basename), provider flags, `--public`/`--private`,
`--desc`, `--branch`, `--no-push`, `--clone PATH`.

### 2. Confirm with a one-liner

```
Creating {private Bitbucket / public GitHub / ...} repo: {name}
```

### 3. Run the script

```bash
/media/data/dev/bain-studio/studio/scripts/repo-create {name} {flags}
```

If it exits non-zero, show the error and stop. If Bitbucket credentials are missing,
the script prompts interactively (Atlassian API token, not app password) — let it run.

### 4. Report

Show the repo URL and, if wired, the remote/branch state. If there were no commits
yet, relay the script's "commit then push" instruction.
