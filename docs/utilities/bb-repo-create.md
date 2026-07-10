---
command: ~/code/bain-studio/studio/scripts/bb-repo-create
invoke: /bb-repo-create
description: Creates a Bitbucket repo and wires up the local git repo — init, remote, push, default branch
tags:
- tool
---

# bb-repo-create — Create a Bitbucket Repo

Creates a new Bitbucket Cloud repository via the API and connects the current
directory's git repo to it in one step: creates the repo, `git init`s if
needed, sets `origin`, pushes, and sets the Bitbucket-side default branch to
match. Wired into [scaffold-dir.md](../gods/hephaestus/scaffold-dir.md) (step 6) so every newly
scaffolded project gets a Bitbucket remote automatically — not left as a
manual follow-up.

## Invoke

```
/bb-repo-create
/bb-repo-create --name my-repo
/bb-repo-create --name my-repo --workspace markbaindesign --branch main
/bb-repo-create --name my-repo --public
/bb-repo-create --name my-repo --no-push
```

## CLI

```bash
~/code/bain-studio/studio/scripts/bb-repo-create --name my-repo --branch main
```

## Parameters

| Flag | Default | Description |
|---|---|---|
| `-n, --name` | current dir basename | Repo name |
| `-w, --workspace` | `markbaindesign` | Bitbucket workspace slug |
| `--branch` | `main` | Default branch, both locally and on Bitbucket |
| `--public` | off (private) | Create as a public repo |
| `--no-push` | off | Create the Bitbucket repo + set default branch only; skip local git init/remote/push |
| `--setup` | — | Re-run credential setup |

## Behaviour

- If the repo already exists (HTTP 400, "already exists"), continues rather than failing — safe to re-run.
- If there are no commits yet in the local repo, sets the remote and stops, printing the `git push -u origin <branch>` command to run once there is a commit. Re-running the script afterward finishes the job (creates nothing new, pushes, sets default branch).
- Sets the Bitbucket-side default branch via a `PUT` after push, since a fresh repo defaults to `master` regardless of what's pushed.

## Required credentials

Shared with `bb-pr` (no dedicated doc yet — see `~/code/bain-studio/studio/scripts/bb-pr`) — read from `BITBUCKET_USER` / `BITBUCKET_APP_PASSWORD` env vars first, falling back to `~/.config/bb-pr` (created on first run via `--setup`).

**Important:** classic Bitbucket app passwords are deprecated and stop working 2026-06-09. Use a scoped Atlassian API token instead:

1. `https://id.atlassian.com/manage-profile/security/api-tokens`
2. **Create API token with scopes** → app: **Bitbucket** → scopes: `read:repository:bitbucket`, `write:repository:bitbucket`
3. `BITBUCKET_USER` must be the **Atlassian account email** (not the Bitbucket username) — auth is `email:api_token`, not `username:app_password`

Currently set globally in `~/.zshrc` (`BITBUCKET_USER="your-cloudways-email@example.com"`) so every project/shell inherits it without per-project setup.

## Related

- [scaffold-dir.md](../gods/hephaestus/scaffold-dir.md) — calls this automatically as part of project scaffolding
