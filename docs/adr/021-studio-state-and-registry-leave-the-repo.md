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
2. ~~**Does the Active projects table in `CLAUDE.md` stay?**~~ **Resolved 2026-11-05: deleted.**
   See the addendum below.
3. **Does `studio/inbox/` move** to `~/.local/state/bain-studio/inbox/`, which means changing
   `postman.py`, or stay put as a deliberate exception?
4. **Does `~/.algolia/pulse-config.json` fold in** to the new layout, or stay where the tool expects it?

### Addendum (2026-11-05): question 2 resolved, the table is deleted

The Active projects table is gone from `CLAUDE.md`, which now points at `docs/projects/`
instead. Commit `f66d85e`.

Taken while cutting always-on context cost, not as part of this ADR's migration. The table
cost ~1,900 characters in every session and sat directly beneath the line "Single source of
truth: `docs/projects/` — do not duplicate project state here", so it was the clearest
instance of the fourth source this ADR complains about. All twenty paths were verified
present in `docs/projects/*.md` frontmatter first; `KF-WEB` lives in `kf.md` and `SLT`'s
path in `sl.md`, which is why neither has a file of its own.

Removing it broke four consumers, all fixed in the same commit: `register-project` lost its
Step 3 (it appended a row), `abderus` and `harvest` now read paths from `docs/projects/`
frontmatter, and the hermes docs for `register-project` and `commission` were corrected.

**This picks "delete it" but not yet "point at the registry".** The XDG registry this ADR
proposes does not exist, so the pointer goes to `docs/projects/` — the very thing open
question 1 may change. When question 1 is settled and the registry moves, the pointer moves
with it, and `/focus` (currently `projects.json`) and `/open` (currently `docs/projects/`)
should be brought onto whatever wins at the same time.

The ADR as a whole stays **Proposed**; only this question is settled.

### Addendum (2026-11-06): question 1 resolved — `docs/projects/` leaves the repo

Open question 1 offered three answers. **The third is taken: moved out of the public repo.**
Settled by instruction — "no client data should go in this repo" — after a release push
prompted a survey of what the repo actually carries.

The survey found client-identifying content in **44 tracked files** of 435, across eight
categories: client names, project files whose *filenames* are client identifiers, live
domains and hosting install hostnames, a Cloudways application ID, two analytics property
IDs, Dropbox client paths, private repository URLs, and Asana project GIDs. Two local feature
branches are themselves named after a client. Nothing is a credential: no token, key or
private key has ever been tracked, and `.env` has never been committed. This is a
confidentiality defect, not a breach.

The count was arrived at twice. A hand-written name regex returned a union of 82 files, which
double-counted the *variable name* `ASANA_PROJECT_GID` and the studio's own repository URLs,
while missing three clients whose names the regex did not anticipate. 44 is the figure a
denylist **generated from the registry** returns. The lesson is recorded here because it is
the same lesson as the rest of this ADR: a hand-maintained list of what the studio works on
disagrees with the real one.

#### What was decided

1. **The split in this ADR is kept, and extended to the prose.** `registry.json` under
   `$XDG_DATA_HOME/bain-studio/` holds identity. The per-project prose — stack, hosting,
   system enrollment, context — becomes a document under `$STUDIO_CONTENT_DIR/projects/`,
   where `documents-in-dropbox.md` already puts documents. The repo keeps nothing per-project.
2. **The registry schema grows beyond this ADR's `path`, `prefix`, `gid`, `name`, `status`.**
   It also carries `client`, `domains`, `repo` and `kind`. Not for the tools: for the
   enforcement denylist, which cannot be generated without them, and which must distinguish
   client entries from internal ones or every commit naming an internal project is refused.
   `kind` is already derivable — half the current project files declare an internal client.
3. **ADRs keep project prefixes and lose everything else.** Once the prefix-to-client mapping
   is out of the repo, a bare prefix identifies nobody, and the toolchain speaks in prefixes
   throughout. Client names, domains, install hostnames and provider IDs go; the detail moves
   to that project's `Dev Ops/` note in Dropbox first, which ADRs 023 and 024 already cite as
   its home. Six ADRs are affected: 016, 017, 018, 019, 023, 024.
4. **Git history is left intact.** No rewrite, no force-push. The repo has no forks, no stars,
   no workflows, no deploy keys and a single contributor, so a rewrite was available and was
   considered; it was declined. The data has been public for roughly six months, a rewrite
   would re-tag the 40 tags the ops worktree is pinned to, and nothing exposed is a credential.
   The rule is met going forward, not retroactively, and this records that deliberately.
5. **`CHANGELOG.md` is redacted going forward only.** Past entries stay as written. The
   identical text is in `git log` either way, so rewriting a dated record would buy a tidier
   snapshot and nothing else. New entries name prefixes.
6. **Enforcement is a hook, not a rule** — the conclusion ADR 026 reached the same day. A rule
   alone is what produced the defect: the "What belongs in this repo" section of `CLAUDE.md`
   listed `docs/projects/` as belonging, three lines below the sentence "It is public." That
   section is rewritten as part of this work.

#### The denylist must never be committed

A list of client names and domains, checked into the public repo so a hook can grep for it, is
the exact data the hook exists to keep out. The denylist is **generated at run time** from
`registry.json`, which is outside the repo. The hook script is versioned; its subject is not.

Three failure modes are designed against, because each one makes the hook useless while
appearing to work:

- **It must scan added lines only.** A diff-wide match refuses the redaction commits themselves.
- **It must also run on the commit message.** `pre-commit` never sees the message, and the
  studio's own rules direct reasoning into commit messages, which are public.
- **It must refuse, not pass, when the registry is absent** — a fresh clone, or another
  machine. An empty denylist otherwise lets everything through silently.

#### Migration order

This ADR's own ordering constraint binds harder here than it did for state, because the ops
worktree runs scheduled jobs off a release tag and several of them read `docs/projects/`
frontmatter. The registry and the out-of-repo config files are written first, then a resolver
that reads them with a fallback to the old location, then a release and `ops-deploy.sh`, and
only then do the files move. The fallback is removed last, once ops is proven on the new
reader.

One collector is invoked from `crontab` by a filename that names a client. Renaming it is a
cron edit in the same change, or the collector stops silently.

The ADR as a whole stays **Proposed**. Question 1 is now settled; questions 3 and 4 are not.
