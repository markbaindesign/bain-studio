---
tags: [utility, terminal, tmux, claude]
command: studio/scripts/session-status
invoke: tmux window `sessions`
description: Dense always-on list of every Claude Code session on the machine, sorted by which one needs Mark first, showing each one's tmux target, context size and what it is working on
---

# session-status

One screen showing every Claude Code session running on this machine, **across every Claude
account**: its status, which tmux pane it is in, its project, how much context it is holding,
how long it has been in that state, and what it is working on. Sorted attention first, then live work, then the parked
sessions - `waiting`, `shell`, `busy`, `idle` - and within a status, longest first. Idle sits
last because a session idle for two days is not asking for anything, while busy is work worth
watching.

```
12 sessions   1 waiting · 1 shell · 1 busy · 9 idle   kf 2 · main 10        1s ago
● waiting  main  mwe:1.1       middlewayeducation        118k    12m  Passiko project setup
◑ shell    main  studio:1.0    Work                      282k    54m  Invoices bookkeeping
◐ busy     main  infra:0.0     bain-studio               159k     3s  Session dashboard rebuild
○ idle     main  ebiz:0.0      ebiz-global               103k    53m  EBiz Japan email migration
○ idle     kf    kf:0.0        kf-21                      82k    49m  Ticket reply directly
○ idle     kf    KF:1.0        kf-21                     168k    49m  Budget update
○ idle     main  infra:0.1     bain-studio (bg)           31k     7m  -
```

Columns are given up as the pane narrows, in order of what can be done without: the title
first, then the context size, then the project is squeezed. Status, tmux target and time in
state always survive. The account column appears only when more than one Claude account has
sessions running; on a single-account machine it would be dead space.

## What moves on screen

Only `waiting` and `shell` pulse - their glyph swaps with `◦`, waiting every tick and shell
every third, so it reads as a slower breath. **Movement means a human is needed and nothing
else**, which is what makes it legible out of the corner of an eye. A spinner on `busy` was
considered and dropped: on a 12-session machine most of the screen would be in motion, and this
pane sits in peripheral vision all day.

Redrawing is decoupled from polling. The screen ticks every 0.5s while something is pulsing,
while `claude agents --json` is still only called every 4s - and with nothing pulsing the loop
drops back to the poll interval rather than waking twice a second to redraw an unchanged
screen. The "Ns ago" stamp ticks smoothly as a side effect.

`curses.A_BLINK` is not used: VTE and tmux render it inconsistently or drop it altogether, so
the pulse is driven by the redraw loop instead.

| Key | Action |
|---|---|
| `j` / `k` / arrows | move |
| `r` | refresh now |
| `g` / `G` | top / bottom |
| `q` | quit |

The app does not switch windows for you. The `where` column is the tmux target, so
`studio:3.0` is reached with `tmux select-window -t studio:3`, or by its number from the
tmux prefix.

## The `shell` status, and why the CLI cannot be trusted alone

`claude agents --json` reports `busy` while **any background shell the session spawned is still
alive** - even when the model finished its turn an hour ago and ended by asking a question.
Found in the wild on 2026-10-30: a session had been sitting on "how should this deposit clear?"
for 54 minutes, reported `busy`, and therefore sorted *last*, under the heading that means
"working, needs nothing". That is the exact case this app exists to surface.

The transcript settles it. A session has finished its turn when its newest user-or-assistant
entry is an **assistant** entry whose `stop_reason` is `end_turn` with no outstanding
`tool_use`. Where the CLI says `busy` and the transcript says finished, the status shown is
`shell`.

It sits in the attention group, directly under `waiting`, and deliberately not merged into
either neighbour: the model is not working, so `busy` is wrong, but a live background shell may
yet wake the session, so it is not simply parked either. The two cases are indistinguishable from the
transcript - a turn that ended with a question and a turn that ended pending a job look
identical - so the label states what is known and leaves the judgement to the reader.

**The newest entry has to be checked, not just the newest `stop_reason`.** At the start of a
turn - prompt in, model still thinking, nothing written yet - the previous turn's `end_turn` is
still the last one in the file. Replaying one real transcript line by line, reading
`stop_reason` alone called **13 of 145 turn-starts** "finished". Every user entry (a prompt or a
tool result) resets it; `test_session_status.py` guards this.

## Where the data comes from

`claude agents --json`, polled every 4 seconds (each call costs about 0.3s of CPU), plus a tail
read of each session's transcript. **No hooks and no database.** Three facts make that possible,
all verified against Claude Code 2.1.314 on 2026-10-30:

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

### What the transcript gives, in the same read

That file is already located for its mtime, so the turn state above, the context size and the
title come out of one tail read of it. **Reparsed only when the mtime moves** - these files
reach megabytes and the poll is every 4 seconds. A full cold collect of 12 sessions takes
0.3s, all of it the `claude agents` subprocesses; the parsing does not register.

- **Context size** is the last assistant `usage`, summing `input_tokens`,
  `cache_read_input_tokens`, `cache_creation_input_tokens` and `output_tokens`. Checked against
  what a session reports in its own footer: 282,746 against its "283.2k".
- **Title** is the newest `aiTitle` entry - Claude Code's own name for what the session is
  doing, and usually the most useful column on the screen.
- The tail read is 256KB, retried at 4MB when it holds no user or assistant entry at all. One
  session needed the wider read: its last 256KB were entirely `api-request-blob` lines.

The seven fields in `claude agents --json` (`pid`, `cwd`, `kind`, `startedAt`, `sessionId`,
`name`, `status`) are all it offers - there is no background-shell count and no context figure
in it, which is why the transcript is read at all.

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
- **Context is shown in tokens, not as a percentage.** The denominator is unsettled: the
  cached model table in the `claude-api` skill gives Opus 5 a 1M window, but that is a single
  source (the Models API's `max_input_tokens` needs API credentials this machine does not
  have), transcripts show Claude Code marking a distinct `claude-opus-5-5[1m]` variant, and a
  session on plain `claude-opus-5` was observed holding 283k - so the unsuffixed ceiling is not
  200K either. Whether Claude Code compacts below the model ceiling is also unknown, which
  would make any percentage flatter than the truth. The absolute figure is verified; a
  percentage would not be.
- A session with no transcript file shows `-` for context and title. Observed once: a live
  session whose `sessionId` had no `.jsonl` anywhere under `~/.claude*`.
- Local machine only. Cloud sessions are not covered.
- One Unix user. Sessions belonging to another OS user are not visible, and `/proc` and
  `tmux list-panes` would not reach them anyway.
- Read-only. It shows where a session is; it does not switch to it. Jumping by key was
  dropped deliberately - `tmux switch-client` moves whichever client the app runs in, which
  with several attached clients is not reliably the one in front of you.
