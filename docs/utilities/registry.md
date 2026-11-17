---
tags: [utility, registry, projects]
god: hermes
command: python3 studio/registry.py
description: Resolves a project prefix to its path, GID and status from the registry outside this public repo, falling back to docs/projects while that migration runs.
---

# registry

One place that knows where project identity lives. Everything else asks it.

```bash
python3 studio/registry.py --list
python3 studio/registry.py --prefix KF-WEB --field path
python3 studio/registry.py --prefix KF-WEB            # the whole entry as JSON
python3 studio/registry.py --json --active
python3 studio/registry.py --source                   # which source answered
```

From Python:

```python
import registry
path  = registry.path_for("KF-WEB")
entry = registry.resolve("KF-WEB")
live  = registry.active()
```

## Where identity lives

`$XDG_DATA_HOME/bain-studio/registry.json`, outside this repo, because the
registry names clients and this repo is public. Each entry carries `kind`,
`prefix`, `name`, `client`, `status`, `path`, `repo`, `gid`, `domains` and
optionally `ga4_property`.

| Override | Replaces |
|---|---|
| `BAIN_REGISTRY` | the registry file |
| `BAIN_PROJECTS_JSON` | the fallback's `projects.json` |

## The fallback, and why half of it is already dead

With no registry it reads `docs/projects/*.md` frontmatter plus `projects.json`.
`--source` says which answered.

**The `docs/projects/` half can no longer fire in this tree.** It was written for
ADR 021's two-release order — ship the reader, deploy it, then move the files —
which would have left a window where this code ran next to that directory. The
work shipped as one release instead, so the resolver and the directory's removal
land in the same commit, and the new code never coexists with the old files. It
survives only for a checkout of an intermediate commit on
`feature/no-client-data`.

What is left is `projects.json`, which carries paths but a prefix for only a
handful of entries, so the fallback is now a thin safety net rather than a
complete answer. **It is removed outright in the last step of BSTD-875.** Nothing
new should be built on it, and nothing should rely on it being complete.

Unlike [gen-denylist](gen-denylist.md), this falls back rather than refusing.
The denylist guard refuses on a missing registry because passing silently would
defeat the guard; here a missing registry has a correct older answer available,
and refusing would stop every scheduled job.

## `repo_root`

`load()`, `resolve()` and `path_for()` take `repo_root`, which scopes the
fallback scan to a caller's own idea of the repo instead of this file's
location. `postman.py` passes its `STUDIO_ROOT`. Without it a caller under test
is silently answered from the real tree, which is exactly how the first version
broke `test_postman.py`.

## Resolution rules

- Prefix matching is case-insensitive and ignores surrounding whitespace.
- An unknown or blank prefix returns `None`; it never raises.
- A malformed or empty registry falls back and warns on stderr.
- `projects.json` never overrides a project file for the same prefix.
- Frontmatter with no `prefix` is skipped.
- `active()` omits `paused` and `archived`.

## Related

- [ADR 021](../adr/021-studio-state-and-registry-leave-the-repo.md) — why identity
  left the repo; the 2026-11-06 addendum settles what `docs/projects/` becomes.
- [gen-denylist](gen-denylist.md) — reads the same registry to build the commit guard.
