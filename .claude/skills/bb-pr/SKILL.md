---
name: bb-pr
description: Create a Bitbucket pull request from the current branch. Wraps ~/code/bain-studio/studio/scripts/bb-pr. Usage: /bb-pr or /bb-pr --base develop --title "My PR"
allowed-tools: [Bash]
---

# bb-pr — Create a Bitbucket Pull Request

Runs `~/code/bain-studio/studio/scripts/bb-pr` to open a PR on Bitbucket from the current branch.

## Usage

```
/bb-pr
/bb-pr --base develop --title "My PR title"
/bb-pr --base master --title "Title" --body "Description"
```

## Steps

### 1. Check the current branch and repo

```bash
git rev-parse --abbrev-ref HEAD
git remote get-url origin
```

Confirm we are on a feature branch (not develop or master) with a Bitbucket remote. If not, warn the user before proceeding.

### 2. Determine arguments

From the user's message, extract:
- `--base` — target branch (default: `develop`)
- `--title` — PR title (default: branch name, but suggest a better one based on the commits)
- `--body` — PR body (optional; summarise what changed if the user wants one)

To get a useful default title, run:
```bash
git log develop..HEAD --oneline
```
Use the commit messages to suggest a concise PR title if the user hasn't specified one.

### 3. Run the script

```bash
~/code/bain-studio/studio/scripts/bb-pr --base "$BASE" --title "$TITLE" --body "$BODY"
```

The script handles:
- Credential loading from `~/.config/bb-pr` (created on first run via `--setup`)
- Confirmation prompt before creating
- JSON encoding and API call

### 4. First-run credential setup

If the script prompts for setup, tell the user:
1. Go to `https://bitbucket.org/account/settings/app-passwords`
2. Create an app password with **Repositories (Read + Write)** and **Pull Requests (Read + Write)**
3. The script saves credentials to `~/.config/bb-pr` (chmod 600) — safe to use on any machine

### 5. Report

Output the PR URL. If the script errors, show the message and suggest checking credentials with `bb-pr --setup`.
