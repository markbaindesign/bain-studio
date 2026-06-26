---
tags: [skill, utility, repo, github, bitbucket]
god: hermes
command: /create-repo
invoke: /create-repo <name> [--private] [--desc TEXT] [--clone PATH]
description: Create a new GitHub (public) or Bitbucket (private) repository. Shell alias available as `create-repo`.
---

# create-repo — Repository Creation

Creates a remote repository and optionally clones it or adds it as `origin` to the current git repo.

- Default: **GitHub public** repo under `markbain/`
- `--private`: **Bitbucket private** repo under the configured workspace

## Invoke

```
/create-repo my-project
/create-repo my-project --private
/create-repo my-project --desc "Client project" --clone ~/code/my-project
```

Or directly from the shell:

```bash
create-repo my-project
create-repo my-project --private --desc "Internal tool"
```

## Options

| Flag | Default | Effect |
|------|---------|--------|
| `--public` | yes | GitHub (public) |
| `--private` | - | Bitbucket (private) |
| `--desc TEXT` | - | Repository description |
| `--no-remote` | - | Skip adding `origin` to current repo |
| `--clone PATH` | - | Clone repo to PATH after creation |
| `--setup` | - | Configure Bitbucket credentials |

## Credentials

- **GitHub**: uses `gh` CLI (must be authenticated via `gh auth login`)
- **Bitbucket**: reads `~/.config/bb-create-repo` or env vars `BITBUCKET_USER` / `BITBUCKET_APP_PASSWORD`. Run `create-repo --setup` to configure.

## Files

- Skill: `.claude/skills/create-repo/SKILL.md`
- Script: `studio/scripts/create-repo`
- Symlink: `~/bin/create-repo` (in PATH)
- Shell alias: `~/.zshrc` line 100