---
command: ~/code/bain-studio/studio/scripts/repo-create
invoke: /repo-create
description: Provider-agnostic repo creation - GitHub or Bitbucket - plus local git wiring (init, remote, push, default branch)
tags:
- tool
---

# repo-create — Create a Repository (any provider)

Merged successor to `create-repo` (GitHub) and `bb-repo-create` (Bitbucket):
one script that creates the repo on either provider and wires the local git
repo to it - `git init` if needed, `origin` set, initial push, and (Bitbucket)
default branch set via API.

## Provider selection

- `--bb` / `--gh` force a provider
- otherwise: **private (default) → Bitbucket, `--public` → GitHub**

## Usage

```bash
repo-create                          # Bitbucket private repo named after cwd
repo-create my-tool --public         # GitHub public repo
repo-create my-repo --gh --private   # GitHub private repo
repo-create -n kf-x -w markbaindesign --branch main
repo-create my-repo --no-push        # create only, skip wiring
repo-create my-repo --clone ~/code/my-repo
repo-create --setup                  # (re)configure Bitbucket credentials
```

## Credentials

- **GitHub:** `gh` CLI (already authenticated)
- **Bitbucket:** Atlassian scoped API token (app passwords disabled 2026-06-09),
  stored in `~/.config/bb-pr` - shared with [bb-pr](bb-pr.md). `BITBUCKET_USER`
  is the Atlassian account email.

## Compatibility

`bb-repo-create` remains as a thin wrapper (`repo-create --bb "$@"`) so existing
docs, muscle memory, and [scaffold-dir](../gods/hephaestus/scaffold-dir.md) step 6
keep working. The old GitHub-only `create-repo` is removed; a shell alias keeps the
name pointing here.
