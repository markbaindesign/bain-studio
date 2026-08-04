---
name: bb-repo-create
description: DEPRECATED alias - use /repo-create. Creates a Bitbucket repo and wires the local git repo. Forwards to studio/scripts/repo-create --bb.
model: haiku
allowed-tools: [Bash]
---

# bb-repo-create — deprecated alias for /repo-create

The repo-creation tools were merged into the provider-agnostic `/repo-create`
(`studio/scripts/repo-create`). This name is kept as a wrapper: run

```bash
/media/data/dev/bain-studio/studio/scripts/repo-create --bb {args}
```

with the same flags as before (--name, --workspace, --branch, --no-push, --public,
--setup). See the repo-create skill for full usage.
