---
tags: [utility, terminal, tmux, git]
command: studio/scripts/repo-status
invoke: tmux window `repos`
description: Dense always-on list of every registered studio repo and what is unfinished in it - uncommitted work, unpushed commits, unmerged branches, extra worktrees - over a line saying whether ops is running the newest release
---

# repo-status

The companion to [session-status](session-status.md). That one answers *which session needs
me*; this one answers *where did I leave work*. One screen, every repo in the registry, sorted
so the ones holding unfinished work are at the top.

```
19 repos   10 dirty · 4 ahead · 1 untracked · 1 branch · 1 ok · 2 nogit            4s ago
ops 1.18.0 current
● dirty     bain.design          develop                      2ub      2M    5h  BD-171 Rebuild page.php
● dirty     beato-properties     develop             ↑14      3ub   1M 2?    7d  Env check: P23 Divi Buil
● dirty     techstyle            feature/compliance  local    1ub  4M 47?   18d  feat: editable page text
▲ ahead     bain-studio          develop             ↑12  7wt 5ub            4m  Merge tag '1.18.0'
▲ ahead     kf-21                feature/cron-inter  local 2wt 5ub           27m  Run Action Scheduler
◌ untracked upwork-proposals     develop                      1wt      1?    5h  docs(changelog): correct
◐ branch    nore                 feature/react-fron           4ub            4d  feat: update output
○ ok        kf-tara-web          develop                                   39d  Merge branch 'feature/ta
· nogit     premium_domains      not a git repo                              -
```

| State | Means |
|---|---|
| `missing` | the registered path is gone - the registry is wrong, or the project was moved |
| `dirty` | tracked changes in the working tree: staged, unstaged or conflicted |
| `ahead` | commits that exist only here, or a branch with no upstream at all |
| `mirror` | nothing changed but the Asana mirror files, waiting to be committed |
| `untracked` | nothing tracked has changed, but there are untracked files |
| `branch` | clean, but parked on something other than `develop` / `main` / `master` |
| `ok` | clean, on the integration branch, everything pushed |
| `nogit` | the path is not a git repository, or git will not read it |

| Column | Means |
|---|---|
| `3M 2m 2?` | three tracked changes, two Asana mirror files, two untracked entries |
| `↑14` | fourteen commits the upstream does not have |
| `local` | the branch has no upstream, so none of it has been pushed |
| `no remote` | the repo has no remote at all - a push has nowhere to go |
| `7wt` | seven worktrees besides the main one |
| `5ub` | five local branches not merged into the integration branch |
| `15d` | time since the last commit |

Columns are given up as the pane narrows, in order of what can be done without: the last
commit subject first, then the parked-work counts, then the branch is squeezed. State, repo
name and the working-tree counts always survive.

## Three kinds of "changed", counted apart

A single dirty count made ten of nineteen repos permanently red, which is the same as sorting
by nothing. Three things were being added together:

- **Real changes** (`3M`) - tracked files Mark edited. This is what `dirty` means.
- **Asana mirror files** (`2m`) - `asana-mirror.md` and `asana-ids.json`, which `sync.py`
  rewrites at the project root on a schedule. In half the client repos they were the *only*
  modified files. A repo with nothing else changed gets the `mirror` state, below `ahead`: it
  still wants a commit, but nobody left work half-done in it.
- **Untracked files** (`2?`) - nearly every project carries an untracked `.claude/` or `.ddev/`
  that will never be committed, and techstyle has 47 of them.

A mirror change alongside real changes is still `dirty`, and unpushed commits still outrank
both: that is the bigger fact about the repo.

### `local` and `no remote` are different problems

A branch with no upstream has not been pushed; a repo with no remote at all has nowhere to push
to, and will sit there for ever looking like unpushed work. The second wants
[repo-create](repo-create.md), not a push, so it is labelled separately.

## Nothing is fetched

Every figure comes from local refs. A poll that talked to a remote would need credentials for
twenty repos and would be slow, and it is not this app's job to decide when to fetch.

That is why **"behind" is not shown at all**. Without a fetch it would be a stale number
dressed as a fact: the row would say "behind 0" about a remote that moved last week. Ahead is
honest, because local commits are local knowledge. So is `local`, which means the branch has no
upstream configured and no `origin/<branch>` to fall back on - work that exists on this machine
and nowhere else.

## The ops line

A tagged release is not done until ops is deployed (ADR 014), so the second line says which tag
the ops worktree holds and whether a newer one exists:

```
ops 1.18.0 current
ops 1.17.0 → 1.18.0 to deploy · 2 local changes
```

Local changes to tracked files are drift too: `ops-deploy.sh` refuses to deploy over them, so a
release can sit undeployed with nothing else on screen saying why. An ops worktree with no tag
on its HEAD is shown by its commit (`ops @dcdb759`).

## Where the data comes from

`studio/projects.json`, then four or five git commands per path, run in a thread pool:

1. `rev-parse --show-toplevel` - the repo root, and the first thing to fail if the path is not a
   repo. The stderr is kept, because "dubious ownership" (which `safe.directory` fixes) is a
   different problem from "not a git repository" (which means the registry is wrong).
2. `status --porcelain=v2 --branch` - branch, upstream, ahead, and the file counts.
3. `worktree list --porcelain` - worktrees, skipping `prunable` entries, which are worktrees
   whose directory has gone and which git keeps listing until someone prunes.
4. `for-each-ref refs/heads` then `branch --no-merged <integration>` - the unmerged count. The
   integration branch is resolved per repo (`develop`, else `main`, else `master`), and the
   integration branches themselves are excluded: `main` not being merged into `develop` is the
   normal state of a git-flow repo, not unfinished work. A `looper/*` branch does count.
5. `log -1` - the age and subject of the last commit.

A branch with no `branch.upstream` is checked against `origin/<branch>` before being called
unpushed, because a branch can be pushed without having its upstream configured. If that ref
does not exist either, `git remote` decides between `local` and `no remote`.

### Every call runs with `GIT_OPTIONAL_LOCKS=0`

Plain `git status` takes `index.lock` to write back refreshed stat information. A pane doing
that to twenty repos a minute would eventually collide with a real `git commit` in one of them
and fail it with "Another git process seems to be running". Nothing here needs the index
refreshed on disk, so the lock is never taken.

### One row per repo, not per registered path

SL and SLT are directories *inside* bain-studio, so three registry paths resolve to one repo.
Rows are deduplicated by the repo's toplevel and the shortest path wins, which is the repo root
rather than a directory in it.

### Why it collects on a thread

A cold pass over twenty repos takes about 3 seconds, a warm one about 0.5 - almost all of it
waiting on disk. Collecting on the draw loop would freeze the screen for that long every
minute, so it runs on a background thread: the screen keeps the last result and says how old it
is, showing `refreshing` while the next one is gathered. A refresh asked for while one is
already running is ignored rather than queued.

The poll is **60 seconds**, not the 4 of session-status. Repo state changes at the speed of
commits, and twenty repos of git is not something to do every 4 seconds.

A pass that throws keeps the previous rows and puts the error in the header. Without that, one
unexpected line of git output would kill the collector thread with its refresh flag still set,
and the pane would say `refreshing` until it was respawned - a stuck screen that still looks
like a working one.

## Keys

| Key | Action |
|---|---|
| `j` / `k` / arrows | move - the selected row's full path appears at the foot |
| `r` | refresh now |
| `g` / `G` | top / bottom |
| `q` | quit |

## Setup

Add a window to `~/.config/bain-studio/tmux.json`:

```json
{"name": "repos", "dir": "/home/bain/ops/bain-studio",
 "cmd": "studio/scripts/repo-status"}
```

Like `sessions` and `monitor`, it points at the ops worktree: an always-on window should run a
released tag, not whatever branch is checked out. **Add it only once a release carrying this
script has been deployed to ops**, or the next `studio-tmux` run opens a pane whose command
does not exist yet.

To add it to a running session without `studio-tmux` moving the view of whoever is attached:

```bash
tmux new-window -d -t "=studio:" -n repos -c /home/bain/ops/bain-studio studio/scripts/repo-status
```

**Deploying is not enough to update it.** The running process holds the old script in memory,
so restart the pane after a deploy:

```bash
tmux respawn-pane -k -t "=studio:repos"
```

See [ops-worktree](ops-worktree.md) and [studio-tmux](studio-tmux.md).

Run it directly with `studio/scripts/repo-status`. Pure stdlib, no dependencies.

The registry is gitignored, and only the ops worktree has it (as a symlink, via
`ops-worktree-link.sh`). To run the script from a development worktree, point it at the
checkout's copy:

```bash
STUDIO_PROJECTS=/media/data/dev/bain-studio/studio/projects.json studio/scripts/repo-status
```

Without a registry the header says so rather than showing an empty list, which would read as
"nothing to do".

## Limits

- **Local only.** No remote is contacted, so `↑` and `local` are about local refs and `behind`
  is absent by design.
- Only **registered, active** projects are read. A project absent from `projects.json`, or
  marked inactive in it, does not appear.
- One row per repo, so work parked in a *worktree* shows only as a count (`7wt`). Which branch
  each worktree is on is a `git worktree list` away.
- Unmerged branches are counted, not listed.
