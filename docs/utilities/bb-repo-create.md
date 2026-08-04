---
command: ~/code/bain-studio/studio/scripts/bb-repo-create
invoke: /bb-repo-create
description: DEPRECATED alias for repo-create --bb - creates a Bitbucket repo and wires the local git repo
tags:
- tool
---

# bb-repo-create — deprecated alias

Merged into the provider-agnostic [repo-create](repo-create.md). The
`bb-repo-create` script survives as a thin wrapper (`repo-create --bb "$@"`),
so all existing flags and invocations - including
[scaffold-dir](../gods/hephaestus/scaffold-dir.md) step 6 - work unchanged.
See [repo-create.md](repo-create.md) for usage and credentials.
