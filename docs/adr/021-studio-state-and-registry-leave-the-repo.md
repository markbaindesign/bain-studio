---
tags: [adr, infrastructure, registry, state, cron]
god: periphetes
description: Studio state and the project registry live inside the dev checkout, so production symlinks backwards into a development directory and project identity is spread across four disagreeing sources. Both move out of the repo, registry separate from state, resolved by XDG paths rather than symlinks.
---

# ADR 021 — Studio state and the project registry move out of the repo

Date: 2026-09-30
Status: Proposed
Amends: [ADR 014](014-ops-worktree-for-scheduled-jobs.md) (its state-sharing mechanism only)
Related: [ADR 011](011-mirrors-at-project-root.md), [ADR 004](004-dashboard-stays-in-repo.md)

## Context

Two problems, found while reviewing the Daily Brief on 2026-09-30. They look separate and are
the same problem: **the studio keeps its data inside a code checkout.**

### Production depends on a development directory

ADR 014 moved scheduled jobs to an ops worktree so that whatever branch was checked out could no
longer decide what ran at 08:00. It shared the gitignored runtime paths by symlinking the ops tree
back into the dev checkout, so that exactly one copy of each exists. That single-copy requirement
is right and this ADR keeps it. The mechanism is what is wrong: there are now **31 symlinks from
`/home/bain/ops/bain-studio` into `/media/data/dev/bain-studio`**, covering the registry, secrets,
collector state, logs and the inbox.

The dependency is therefore inverted. Cron reads its secrets and its state out of a working tree
that exists to be edited, branched and rebuilt. Moving, re-cloning or cleaning that directory
breaks every scheduled job at once.

The same assumption is baked into the scripts: **24 state and log paths are built from
`Path(__file__)`**, which ADR 014 explicitly warned against for exactly this reason, and which
only works today because the symlinks paper over it.

### Project identity has four sources, and they disagree

| Source | Tracked | Holds | Observed gaps |
|---|---|---|---|
| `studio/projects.json` | gitignored; drives `sync.py` and the Daily Brief | path, status | only 3 of 18 entries carry `prefix`/`gid`/`name` |
| `docs/projects/*.md` | **tracked, public repo** | prefix, status, path | no file for one active project |
| Active projects table in `CLAUDE.md` | tracked | prefix, path | two projects absent entirely |
| each project's own `CLAUDE.md` | tracked, per project | `ASANA_TASK_PREFIX` | the only prefix source for 15 of 18, so tools open every project's `CLAUDE.md` to resolve one |

`studio/projects.md` is generated from the first. **32 consumers** read one or more of these: 20
skills and 12 scripts and docs. `register-project` writes several of them, which is where the
duplication is manufactured.

The cost is not theoretical. Pausing one project today took two edits in two files, and until then
neither file had recorded a pause that had been in force for weeks, so the Daily Brief kept
reporting the project as active and produced 20 findings about it.

State has also been accreting wherever each tool found convenient: the Algolia keep-alive registry
lives in `~/.algolia/`, known to nothing else in the studio.

## Decision (proposed)

Studio data and state leave the repo. The registry is separate from the state. Both stay local.

```
~/.local/share/bain-studio/     registry.json        portable data, worth backing up
~/.local/state/bain-studio/     collector state, logs, inbox   regenerable, machine-specific
~/.config/bain-studio/.env      secrets, separate permissions
```

`registry.json` becomes the single source of truth for project identity, with one schema for every
entry: `path`, `prefix`, `gid`, `name`, `status`. Nothing else stores status or path.

Paths resolve **in code**, defaulting to the XDG locations, with an environment variable only as an
override. Cron gets no shell environment, and the `.env` cannot be the thing that says where the
`.env` is, so neither may be load-bearing.

## Reasoning

**Why the registry is split from the state.** They have opposite properties. The registry is small,
portable, worth backing up, and would be meaningful on another machine. Collector state and logs
are machine-specific: syncing them would corrupt run state, and ADR 014 records what divergent
collector state costs, with `wp_pulse` re-summarising 42 posts instead of 3. Keeping them in one
directory would force one backup policy onto both.

**Why local rather than Dropbox.** Both are machine-scoped in practice, and the run state must
never be synced between machines. This follows the split above rather than the precedent of
`$STUDIO_CONTENT_DIR`, which holds documents, not state.

**Why not more symlinks.** A symlink still names one tree as the real home. The point is that
neither tree should be the home: both resolve the same absolute path, and ops stops depending on
the dev checkout existing at all.

**Why XDG rather than an invented directory.** `$XDG_STATE_HOME` defaults to `~/.local/state` and
is specified for "state data that should persist between restarts but is not important or portable
enough that it should be stored in `$XDG_DATA_HOME`", naming logs and history explicitly;
`$XDG_DATA_HOME` defaults to `~/.local/share`. That is precisely the split above, already named.
Sources: the [freedesktop basedir specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest)
and the [Arch Wiki's XDG Base Directory page](https://wiki.archlinux.org/title/XDG_Base_Directory).

**Why gitignoring is not enough.** It keeps data out of git. It does not stop the data living in
the repo, or production depending on the repo's location. The studio already applies "code repos
are for code" to documents; this applies it to state.

## Carve-outs

- **Asana mirrors stay at project root.** `asana-mirror.md` and `asana-ids.json` are a project's
  own data, pinned there by [ADR 011](011-mirrors-at-project-root.md). They do not move.
- **`studio/inbox/` is `postman.py`'s contract.** Moving it means changing postman. Open question
  below.
- **The dashboard stays in the repo** per [ADR 004](004-dashboard-stays-in-repo.md). It is code.

## Migration order

Cron must never be left without its state; ADR 014 records what that costs.

1. Ship code that reads the new path and falls back to the old one.
2. Deploy it with `ops-deploy.sh`, so ops is running the fallback-capable version.
3. Move the files.
4. Remove the symlinks and retire `ops-worktree-link.sh`.
5. Remove the fallback, and with it the `Path(__file__)` state paths.
6. Backfill `registry.json` to one schema, and make `register-project` write only it.

## Consequences

- **`ops-worktree-link.sh` is retired**, and with it the rule that it must be re-run whenever a new
  gitignored runtime path appears, which was a standing way to break a collector silently.
- **32 consumers must be updated.** Most read the registry through `sync.py`, but the 20 skills
  reference paths in prose and need reading individually.
- **`docs/projects/` and the `CLAUDE.md` table can no longer hold status or path.** What they
  become is the main open question, and it contradicts the current `CLAUDE.md` line naming
  `docs/projects/` the single source of truth.
- **A public repo stops carrying the studio's project status.** The registry moves out of it.
- **One-off state directories like `~/.algolia/` become the exception to fold in later**, not the
  pattern to copy.

## Acceptance criteria

- A project's status changes in **exactly one place**, and every consumer sees it.
- `find /home/bain/ops/bain-studio -type l -lname '/media/data/dev/*'` returns nothing.
- No script builds a state or log path from `Path(__file__)`.
- Deleting and re-creating the dev checkout leaves every scheduled job working.

## Open questions

1. **What do `docs/projects/*.md` become?** Prose notes with `status` and `path` removed, generated
   wholesale from the registry, or moved out of the public repo? This overrides the "Single source
   of truth: `docs/projects/`" line in `CLAUDE.md`.
2. **Does the Active projects table in `CLAUDE.md` stay?** It is already the most drifted of the
   four. Generate it, or delete it and point at the registry.
3. **Does `studio/inbox/` move** to `~/.local/state/bain-studio/inbox/`, which means changing
   `postman.py`, or stay put as a deliberate exception?
4. **Does `~/.algolia/pulse-config.json` fold in** to the new layout, or stay where the tool expects it?
