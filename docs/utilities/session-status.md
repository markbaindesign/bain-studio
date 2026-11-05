---
tags: [utility, terminal, tmux, claude]
command: studio/scripts/session-status
invoke: tmux window `sessions`, or the pinned conky panel on the third monitor (`--conky`)
description: Dense always-on list of every Claude Code session on the machine, sorted by which one needs Mark first, under a column legend, showing each one's tmux target, model, context size and what it is working on, over a quota header for every account
---

# session-status

One screen showing every Claude Code session running on this machine, **across every Claude
account**: its status, which tmux pane it is in, its project, the model it is on, how much
context it is holding, how long it has been in that state, and what it is working on - under a
header giving each account's five-hour and weekly quota, over a legend naming each column.
Sorted blocked first, then the parked sessions, then the ones working - `waiting`, `shell`,
`idle`, `working` - and within a status, most recently active first. Working sits last because
a session mid-turn is asking for nothing, while an idle one may be waiting to be picked up.

```
12 sessions   1 waiting · 1 shell · 9 idle · 1 working   bain 10 · kf 2     1s ago
bain 5h 42% →22:20 · wk 64% →Tue   kf 5h 4% →23:40 · wk 11% →Sun
  status   acct  where         project                  model   ctx ctx%   last  title
● waiting  bain  mwe:1.1       middlewayeducation        o5.5  118k  12%    12m  Passiko project setup
◑ shell    bain  studio:1.0    Work                      o5.5  282k  28%    54m  Invoices bookkeeping
○ idle     bain  infra:0.1     bain-studio (bg)          s5.5   31k   3%     7m  -
○ idle     kf    kf:0.0        kf-21                       o5   82k   8%    49m  Ticket reply directly
○ idle     kf    KF:1.0        kf-21                     o5.5  168k  17%    49m  Budget update
○ idle     bain  ebiz:0.0      ebiz-global               s5.5  103k  10%    53m  EBiz Japan email migration
◴ working  bain  infra:0.0     bain-studio                 o5  159k  16%     3s  Session dashboard rebuild
```

The legend is laid out by the same code as the rows, so it names only the columns that fit and
breaks where they break at every width.

Columns are given up as the pane narrows, in order of what can be done without: the title
first, then the context percentage, then the model, then the context size, then the project is
squeezed. Status, tmux target and time in state always survive. Every row keeps the same column
widths whether or not it has a model and a percentage to show, so a session that has not
reported one does not pull the rest of its row out of line. The account column appears only
when more than one Claude account has sessions running; on a single-account machine it would be
dead space. Each account is named after the domain of the signed-in email - `bain`, `kf` - the
same names the status line shows, so a row here and a prompt there are obviously the same
account.

## The quota header

The second line is the rate limit of every account: the five-hour window with the clock time it
resets, and the weekly window with the day it resets. It is the figure that decides whether to
start something or finish what is open, and it belongs next to the sessions that are spending
it.

```
bain 5h 42% →22:20 · wk 64% →Tue   kf 5h 4% →23:40 · wk 11% →Sun
```

The line is dim until it matters: amber from 70%, red from 90%, taking whichever is worst of
either window of either account, since any one of them can be the thing that stops work.

Where a window has already reset since the figure was taken, the percentage is a dead number
from a window that is gone, so the line says `5h reset` or `wk reset` rather than quoting it,
and that figure is left out of the colour. The weekly one is the likelier of the two: an
account left unused past its reset keeps last week's percentage in the file. A weekly reset
less than a day out is given a clock time rather than a weekday, because "→Fri" on a Friday
reads as next Friday.

## What moves on screen

Each status moves in its own way, so a glance tells you the kind of thing you are looking at
before you read a word:

| Status | Motion | Colour |
|---|---|---|
| `waiting` | pulses every tick - glyph swaps with `◦` | red |
| `shell` | pulses every third tick, a slower breath | cyan |
| `idle` | still | orange |
| `working` | spins clockwise, `◴ ◷ ◶ ◵` | green |

Pulsing is reserved for the two statuses that want a human; `working` spins instead, so work in
progress is visibly alive without imitating them. The spinner's quadrants are deliberately
distinct from `◐` (working at rest) and `◑` (shell) so no status can impersonate another
mid-cycle - a unit test asserts it.

Green on `working` and orange on `idle` say which rows need reading: a session mid-turn needs
nothing, a parked one may be waiting for a prompt. Orange is the 256-colour index 208, with
yellow as the fallback on an eight-colour terminal; green is index 71, a muted one rather than
the basic green. The quota header keeps its own amber on colour pair 2, so recolouring the rows
does not touch it.

Redrawing is decoupled from polling. The screen ticks every 0.5s while anything is moving,
while `claude agents --json` is still only called every 4s - and with every session parked the
loop drops back to the poll interval rather than waking twice a second to redraw an unchanged
screen. The "Ns ago" stamp ticks smoothly as a side effect.

`curses.A_BLINK` is not used: VTE and tmux render it inconsistently or drop it altogether, so
the pulse is driven by the redraw loop instead.

| Key | Action |
|---|---|
| `j` / `k` / arrows | move - and summon the cursor, which is hidden until first used |
| `r` | refresh now |
| `g` / `G` | top / bottom |
| `q` | quit |

There is no cursor on launch. It appears on the first `j`/`k` and brings the selected
session's working directory up on the bottom line; until then nothing is highlighted, because a
reversed top row reads as a selection on a screen that is almost always only read.

The app does not switch windows for you. The `where` column is the tmux target, so
`studio:3.0` is reached with `tmux select-window -t studio:3`, or by its number from the
tmux prefix.

## The pinned panel on the third monitor

`session-status --conky` prints the same screen once as conky markup and exits. It is what
feeds `~/.config/conky/studio-claude.conf`, a panel pinned to the right half of the third
monitor - the slot a second Terminator window used to hold.

**The reason is focus, not space.** Running the app in a terminal on that screen made it a
second Terminator window, and getting back to the one holding the tmux sessions meant cycling
*within* the app: `switch-windows` is disabled and `switch-applications` is `<Super>Tab`, which
groups both windows under Terminator. Clicking the Terminator launcher icon had the same
problem - it raised whichever of the two it felt like. A dash is read, not typed into, so the
fix is to stop it being a window at all.

Conky's `panel` window type is `_NET_WM_WINDOW_TYPE_DOCK` with `SKIP_TASKBAR`, `SKIP_PAGER` and
`STICKY` set (verified with `xprop` on the running panel), which keeps it out of `Super+Tab`
and out of the launcher icon's reach - that icon now has only the working terminal to raise.
It also defines struts, which is the other half of the bargain: the work area shrinks from
5760 to 4796 px wide, so a maximized window on that monitor stops at the panel's edge instead
of covering it.

| | |
|---|---|
| Panel | `~/.config/conky/studio-claude.conf` |
| Launcher | `~/bin/studio-claude-dash {start\|stop\|restart\|toggle\|status}` |
| Autostart | `~/.config/autostart/studio-claude-dash.desktop`, 10s after login |

Those three are desktop configuration, so they sit with the other studio panels rather than in
this repo; only the `--conky` mode is here. The panel invokes the **ops worktree** copy, like
the `claude-sessions-status` alias, so it runs a released tag. Unlike the tmux window, it needs
no respawn after a deploy: every refresh is a new process, so the next tick picks the new
script up.

It is deliberately **not** in `studio-conky`'s `PANELS` list. Those panels are a cheatsheet
toggled with `Super+c`, and hiding them should not take the dash down.

### What is different on a panel

- **Only `waiting` moves.** It blinks, with conky's `${blink}`. The spin and the slower
  `shell` breath are gone: they were driven by a redraw loop that a one-shot process does not
  have, and a thing in the corner of the eye all day has to spend movement carefully - anything
  else that moved would train the eye to ignore the one status that is asking for something.
  `${blink}` toggles **once per `update_interval`**, not per refresh, which is why the panel
  draws at 1s while its `execpi` still only runs the script every 5s: at `update_interval = 5`
  the pulse was a five-second stare. Confirmed by sampling the glyph's mean brightness over
  four one-second crops - it alternates.
- **Statuses keep their colours**, as hex rather than 256-colour indexes, so a row means the
  same thing on the panel as in the terminal. A unit test holds the two palettes together.
- **The tally line takes the colour of the most demanding status present**, so the panel
  answers "does anything want me?" before a row is read.
- **The glyph and the reset arrow name their own font.** Roboto Mono for Powerline, which the
  studio panels use, has neither the status circles nor `→` (`fc-list ":charset=25d0"` returns
  nothing for it), and conky drives Xft directly - a comma-separated family list in the config
  is *not* a fallback chain, it takes the first family and draws a blank. So those characters
  are wrapped in `${font DejaVu Sans Mono:size=11}` and switched back, set by `--glyph-font`
  because `${font}` with no size does not inherit the panel's.
- **Columns are fixed pixel `${goto}`s, not padding**, because conky lays text out
  proportionally once `${goto}` is in play and a padded row drifts. There is no narrowing
  ladder: the panel has one width.
- **`$` in a title or project name is escaped to `$$`.** It is conky's variable sigil, and an
  unescaped one swallows the rest of the line.
- **The transcript cache is cold on every refresh**, since each one is a new process. A full
  collect is ~0.4s of CPU, all of it local with no API call, which the 5-second `execpi`
  interval absorbs. `claude` is found on the session PATH at login (`~/.local/bin` is on it),
  which matters because `run()` swallows a failed call and the panel would read "no sessions"
  rather than saying anything was wrong.
  `own_window_argb_visual` is off: the panel type cannot take an ARGB visual (conky dies with a
  BadMatch on `X_CreateWindow`), so it is opaque where the others sit at 96%.

## The `shell` status, and why the CLI cannot be trusted alone

`claude agents --json` reports `busy` while **any background shell the session spawned is still
alive** - even when the model finished its turn an hour ago and ended by asking a question.
Found in the wild on 2026-10-30: a session had been sitting on "how should this deposit clear?"
for 54 minutes, reported `busy`, and therefore sorted *last*, under the heading that means
"working, needs nothing". That is the exact case this app exists to surface.

The transcript settles it. A session has finished its turn when its newest user-or-assistant
entry is an **assistant** entry whose `stop_reason` is `end_turn` with no outstanding
`tool_use`. Where the CLI says `busy` and the transcript says finished, the status shown is
`shell`. Everywhere else the CLI's `busy` is shown as `working`, which is what it means to a
reader; `busy` below is always the CLI's own word, never a status on screen.

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

The account name comes from `oauthAccount.emailAddress` in that account's `.claude.json` -
inside the config directory for a second account, but `~/.claude.json` for the default one,
which is where Claude Code itself keeps it. The domain is mapped to the short label
(`bain.design` -> `bain`, `khyentsefoundation.org` -> `kf`), unmapped domains falling back to
their first label. The map is a copy of the one in `~/.claude/hooks/statusline.py`: that file
is outside this repo, and the app runs from the ops worktree, so it cannot be imported. A read
is cached once it succeeds, because Claude Code rewrites `.claude.json` often enough that a
4-second poll catches it mid-write. Signing out and into a different account in a config
directory therefore needs the pane respawned before the name catches up.

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

### Quota and context percentage, from the status line's own files

Two things neither the CLI nor the transcript can give are read from files
`~/.claude/hooks/statusline.py` already writes on every render:

- **The quota**, from `<config dir>/ratelimit-current.json` - `current_pct`, `reset_ts`,
  `weekly_pct`, `weekly_reset_ts`. One file per account, written to the config directory the
  session is running under, so the two accounts' quotas never overwrite each other.
- **The model and context percentage**, from `~/.claude/logs/sessions/<sessionId>.json`,
  which joins to a row on the `sessionId` the CLI already reports. That path is hardcoded in
  the hook rather than resolved per account, so a KF session's snapshot lands there too -
  one directory to read, not one per account.

The transcript gives a token count; the percentage needs the size of the context window, which
only the status line is told. Both figures are therefore snapshots **taken at the last
status-line render**, not live readings - fresh for anything that has been working, and as old
as its last turn for a session that has been parked for a day. That is why a five-hour window
whose reset time has passed is shown as `reset`: the file is not wrong, it is just describing a
window that has since rolled over.

There is a second writer of `ratelimit-current.json`, `~/.claude/hooks/save-ratelimit.sh`,
which writes only the two five-hour fields and would blank the weekly ones. Nothing calls it:
no `settings.json` under `~/.claude*` or any project in `/media/data/dev`, no crontab, no user
systemd unit. If it is ever hooked up, the weekly half of this header goes with it.

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

For the pinned panel instead of a tmux window, see [the panel section](#the-pinned-panel-on-the-third-monitor): `studio-claude-dash start`.

## Limits

- Linux only (reads `/proc`).
- The quota, model and context percentage are **as fresh as the last status-line render of
  that session or account**, not live. A session that has been parked all day reports the
  context it had when it stopped.
- The quota header depends on `~/.claude/hooks/statusline.py`, which lives outside this repo.
  Replace the status line and the header goes blank - the sessions list carries on.
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
