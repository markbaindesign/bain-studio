---
tags: [utility, terminal, tmux, claude]
command: studio/scripts/session-status
invoke: tmux window `sessions`
description: Dense always-on list of every Claude Code session on the machine, sorted by which one needs Mark first, showing the tmux target of each
---

# session-status

One screen showing every Claude Code session running on this machine, **across every Claude
account**: its status, which tmux pane it is in, its project, and how long it has been in that
state. Sorted so anything needing Mark is at the top - `waiting`, then `idle`, both of which
want a human - and `busy` last, longest first.

```
12 sessions   1 waiting · 1 busy · 10 idle   kf 2 · main 10     1s ago
● waiting  main  mwe:1.1       middlewayeducation          12m
○ idle     main  ebiz:0.0      ebiz-global                 53m
○ idle     kf    kf:0.0        kf-21                       49m
○ idle     kf    KF:1.0        kf-21                       49m
○ idle     main  infra:0.1     bain-studio (bg)             7m
○ idle     main  -             theme-review                 7m
◐ busy     main  infra:0.0     bain-studio                  3s
```

The account column appears only when more than one Claude account has sessions running; on a
single-account machine it would be dead space.

| Key | Action |
|---|---|
| `j` / `k` / arrows | move |
| `r` | refresh now |
| `g` / `G` | top / bottom |
| `q` | quit |

The app does not switch windows for you. The `where` column is the tmux target, so
`studio:3.0` is reached with `tmux select-window -t studio:3`, or by its number from the
tmux prefix.

## Where the data comes from

`claude agents --json`, polled every 4 seconds (each call costs about 0.3s of CPU). **No hooks and no
database.** Three facts make that possible, all verified against Claude Code 2.1.314 on
2026-10-30:

1. `claude agents --json` enumerates every session on the machine across all projects -
   interactive and background - with `pid`, `cwd`, `sessionId`, `name`, `startedAt` and `status`.
2. `status` is `busy`, `idle` or `waiting`, where **`waiting` means the session is sitting on a
   permission prompt**. Confirmed by direct test: a session prompted to run an un-allowlisted
   command reports `waiting` while the prompt is on screen.
3. A session that is closed drops out of the list (observed). A *crashed* session was not
   tested, so the app does not rely on it: `collect()` skips any session whose `/proc/<pid>`
   no longer exists. Either way nothing can sit at "busy" forever, and no timer is needed.

### One call per account

`claude agents --json` reports **only the config directory it is invoked with**. Mark runs KF
under a second Claude account (`CLAUDE_CONFIG_DIR=~/.claude-kf`), and a single call from the
default account silently omitted both of its sessions - 10 reported where 12 were running. This
is a quiet failure: the missing sessions look like sessions that do not exist, which is exactly
the thing the app is meant to prevent.

So every `~/.claude*` directory that contains a `projects/` folder is queried, each in its own
subprocess, run in parallel so the redraw is not stalled by ~0.3s per account. The `projects/`
test is what distinguishes a real config directory from `~/.claude.json` or a backup folder. A
third account needs no code change: create it and it is picked up on the next poll.

Last-activity time is the mtime of the session transcript at
`<config dir>/projects/<slug>/<sessionId>.jsonl`, falling back to `startedAt`. It is resolved
per account, so a KF session's transcript is looked for under `~/.claude-kf`, not `~/.claude`.

The tmux location is resolved by taking the session `pid`, walking `/proc/<pid>/stat` ancestors,
and matching against `#{pane_pid}` from `tmux list-panes -a`. On a 13-session sample this
resolved 12; the unresolved one had no `TMUX` variable in `/proc/<pid>/environ`, so it was
genuinely outside tmux, and shows as `-`.

Rows marked `(bg)` are background agents dispatched from another session. They resolve to the
pane of the session that spawned them, so two of them can share a target.

## Why not `claude agents`

The built-in `claude agents` TUI is **scoped to the current project and lists background agents
only**. Launched from `/media/data/dev/bain-studio` it showed 2 background agents and none of
the 12 live interactive sessions. Only the `--json` form is global. That is the entire reason
this script exists.

## Setup

Add a window to `~/.config/bain-studio/tmux.json`:

```json
{"name": "sessions", "dir": "/home/bain/ops/bain-studio",
 "cmd": "studio/scripts/session-status"}
```

It points at the ops worktree, not the development checkout, for the same reason the
`monitor` window does: an always-on window should run a released tag, not whatever branch
is checked out.

**Deploying is not enough to update it.** The running process holds the old script in memory,
so `ops-deploy.sh` changes the file under it and nothing on screen changes. Restart the pane
after a deploy, which reruns its original command in its original directory:

```bash
tmux respawn-pane -k -t "=studio:sessions"
```

See [ops-worktree](ops-worktree.md).

`studio-tmux` creates the window on the next full run, but it also selects the first window
and switches the client, which moves the view of anyone attached. To add it to a running
session without that, use `tmux new-window -d -t "=studio:" -n sessions -c /home/bain/ops/bain-studio
studio/scripts/session-status`. See [studio-tmux](studio-tmux.md).

Run it directly with `studio/scripts/session-status`. Pure stdlib, no dependencies.

## Limits

- Linux only (reads `/proc`).
- Local machine only. Cloud sessions are not covered.
- One Unix user. Sessions belonging to another OS user are not visible, and `/proc` and
  `tmux list-panes` would not reach them anyway.
- Read-only. It shows where a session is; it does not switch to it. Jumping by key was
  dropped deliberately - `tmux switch-client` moves whichever client the app runs in, which
  with several attached clients is not reliably the one in front of you.
