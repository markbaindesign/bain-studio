---
command: ~/code/bain-studio/studio/scripts/bb-pr
invoke: /bb-pr
description: Create a Bitbucket pull request from the current branch
tags:
- tool
---

# bb-pr — Create a Bitbucket Pull Request

Creates a PR on Bitbucket Cloud from the current branch via the API.
Credentials: Atlassian scoped API token in `~/.config/bb-pr`, shared with
[repo-create](repo-create.md).

## Usage

```bash
bb-pr                                    # PR from current branch, default base
bb-pr --base develop --title "My PR"
```

Invoke as `/bb-pr` or run the script directly.
