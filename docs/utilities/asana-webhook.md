---
tags: [utility, ops, asana, agents]
god: hermes
command: python3 studio/asana_webhook.py {watch|unwatch|status|session-start|session-end|serve|register|unregister|list|catchup}
invoke: /project-watcher
description: Asana webhook listener that has DevBot answer Mark's comments and assignments on a watched project within about a minute, each run in its own git worktree so it never touches the checkout Mark is working in
---

# Asana webhook listener

While you work on a project, you hand DevBot tasks and comment on them. This listener gets the
bot to respond in about a minute instead of at the next session. Decision record:
[ADR 025](../adr/025-asana-webhooks-wake-project-agents.md).

```
Asana ──HTTPS──> Tailscale Funnel ──> 127.0.0.1:$ASANA_WEBHOOK_PORT/asana/{PREFIX}
                                         │  verify X-Hook-Signature, drop irrelevant events,
                                         │  drop everything for an unwatched project,
                                         │  write a queue file, return 200 (< 10 s)
                                         ▼
                                      worker thread
                                         │  fetch story/task from the API, debounce 20 s,
                                         │  one run per task, 2 per project, 3 in all,
                                         │  cap 3 runs per task per hour
                                         ▼
                 claude -p --model opus  (cwd = the task's own worktree)
```

## Watching a project

Nothing runs for a project until it is watched. **Opening a Claude session in the project
watches it**, with no command to remember. You can also watch one by hand:

```
/project-watcher BD                          # or: python3 studio/asana_webhook.py watch BD
python3 studio/asana_webhook.py unwatch BD
python3 studio/asana_webhook.py status
```

`watch` registers the project's webhook if it has none, marks the project watched and queues
any bot task whose latest comment from you has no reply yet, so what you said just before is
not missed. Watch two or three projects at once if you like.

While a Claude session is open in the project, it stays watched. Watching stops **30 minutes
after the last session there closes or your last activity** on the project's bot tasks,
whichever is later. Activity is a comment from you or PmBot, or a task assigned to the bot; the
bot's own replies do not count. If a run is still going, watching stops when it finishes.
Slack says when it stops.

**A lapsed watch starts again on your comment.** A comment from you on a bot task in a
project whose watch lapsed watches it again and queues that task; Slack says so. After
`unwatch`, or in a project never watched, events are dropped, not saved: `watch` picks them
up with its sweep.

Sessions by bots never count: webhook runs (`BAIN_BOT_RUN`), looper sessions
(`LOOPER_RUN_ID`) and anything working in a bot worktree.

### Session hooks

A `SessionStart` and a `SessionEnd` hook run `asana_webhook.py session-start` and
`session-end`. Install them once per machine, from the checkout the listener runs from:

```
python3 studio/scripts/install-watch-hooks.py           # show what would change
python3 studio/scripts/install-watch-hooks.py --apply   # ~/.claude and ~/.claude-kf
```

The hooks are async, print nothing and always exit 0. A session that ends without
`SessionEnd` firing (a crash, a kill) is caught by the listener checking the session's Claude
process every few seconds.

## What wakes the bot

All three need the event to be authored by a user in `ASANA_WEBHOOK_TRIGGER_USERS` (Mark and
PmBot), and the task to be open and assigned to DevBot (`ASANA_BAINBOT_GID`):

| Event | Example |
|---|---|
| Comment added to a task | Mark asks a question on a bot task |
| Task assignee changed | Mark assigns a task to DevBot |
| Task added to the project | PmBot creates a task already assigned to DevBot |

Never: DevBot's own events (no self-triggering), system events, and **comments from anyone
else, including clients**. Asana text is untrusted data; a public endpoint must not let a client
comment start an agent with tools.

A `Review:` or `Done:` note hands the task back to you (`sync.py` reassigns it). From then on
your comments on it wake nothing, unless the comment @-mentions DevBot: that wakes it on the
task as it stands, still assigned to you. To hand the whole task back, assign it to DevBot.

## What a run does

Each task gets its own run, in its own git worktree outside the project:
`$XDG_DATA_HOME/bain-bot-worktrees/{PREFIX}/{LOCAL-ID}`, on branch `bot/{LOCAL-ID}`,
taken from `develop` (or `main`). Later runs on the same task reuse it. The checkout you work in
is readable but never editable.

The prompt (`AGENT_PROMPT`) has the bot read `CLAUDE.md` and the task thread, then:

- **A question or decision:** answer it, change nothing, post `Answer: ...`.
- **Work:** do it in the worktree, commit on `bot/{LOCAL-ID}`, post `Review: ...` with a `Check:` block.
- **Needs your call:** post `Blocked: ...` and stop.

`Answer`, `Review`, `Blocked` and `Done` notes all mention you, so they reach the Mentioned
inbox and Slack. One comment per run, at the end. When the run exits, a worktree with no
commits and no changes is removed with its branch; one with work stays for you to review and
merge.

## Permissions

Runs start with `--restricted --strict-mcp-config`: no settings files and no MCP servers are
loaded, so `run_allow_rules()` is the whole allow-list: `Read`, `Glob`, `Grep`, `Edit` inside
the run's worktree only, `sync.py --get-task` and `--comment` (never a project sync, which
would rewrite the mirror you may be editing), and git `status`, `diff`, `log`, `show`, `add`,
`commit`.
No checkout, branch or git flow commands: from a worktree they act on the whole repository.
The deny-list is the voice agent's `OUTWARD_TOOLS`, the whole Asana MCP, `WebFetch`,
`WebSearch`, every edit inside the project checkout, edits to `.git/**`, `.claude/**` and
`.envrc`, and reads of credential files (`SECRET_FILES`). Git hooks are off
(`GIT_CONFIG_PARAMETERS='core.hooksPath=/dev/null'`). Never `--dangerously-skip-permissions`.
Runs can **read, not write**, the studio registry (`$XDG_DATA_HOME/bain-studio/`) and the
project's Dropbox folder (the `DROPBOX_FOLDER:` line in its `CLAUDE.md`): each is added with
`--add-dir` and given an `Edit` deny and the credential-file `Read` denies. A Dropbox edit has
no branch to review, so a task that needs one ends in a `Blocked:` saying what to write. The
worktrees sit outside `bain-studio/` for this reason: a deny on the registry folder would
otherwise also deny the worktrees inside it.
A project whose `.envrc` exports `CLAUDE_CONFIG_DIR` (KF) runs on that account
([ADR 017](../adr/017-per-client-looper-queues.md)).

## Limits

| Limit | Value |
|---|---|
| Runs per task at a time | 1: comments that arrive meanwhile are handled by one run after it |
| Runs per project at a time | 2 (`MAX_RUNS_PER_PROJECT`) |
| Runs in all at a time | 3 (`MAX_RUNS_TOTAL`) |
| Runs per task per hour | 3, then Slack flags a possible comment loop |
| Run length | 60 minutes, then SIGTERM to the process group, SIGKILL 30 s later |
| Model | `ASANA_WEBHOOK_MODEL`, default `opus` |

Runs use your Max plan, the same limit as your interactive sessions. A run that stops at the
usage limit posts nothing; Slack says so, and you comment again once it resets.

## Setup

Config in `studio/.env`:

```
ASANA_WEBHOOK_TRIGGER_USERS=<Mark GID>,<PmBot GID>
ASANA_WEBHOOK_URL=https://<machine>.<tailnet>.ts.net/asana
ASANA_WEBHOOK_PORT=8787
```

1. Expose the listener: `tailscale funnel --bg --set-path /asana http://127.0.0.1:8787`
2. Install and start the services (they run from the ops worktree, [ADR 014](../adr/014-ops-worktree-for-scheduled-jobs.md)):
   ```
   cp studio/scripts/systemd/asana-webhook* ~/.config/systemd/user/
   systemctl --user daemon-reload
   systemctl --user enable --now asana-webhook.service asana-webhook-catchup.timer
   ```
   User lingering must be on (`loginctl show-user $USER -p Linger`) for it to start at boot.
3. `/project-watcher {PREFIX}` registers each project the first time you watch it. The
   listener must be live: Asana sends the `X-Hook-Secret` handshake during registration, and
   the listener accepts one only for 2 minutes after registration arms it.

Any project in the studio registry can be watched; there is no per-project list to maintain.

## Daily repair

`asana-webhook-catchup.timer` runs `catchup` at 07:45. It re-registers a webhook Asana has
deactivated or deleted (Asana deletes one after 24 hours of failed deliveries), only for a
project registered before. It never starts a run.

## Files

State lives outside the repo, under `$XDG_STATE_HOME/bain-studio/asana-webhook/`:

| Path | Holds |
|---|---|
| `webhook.log` | handshakes, rejections, watch changes, queues, launches, exits |
| `runs/{PREFIX}-{LOCAL-ID}-{stamp}.log` | full output of each run |
| `watch.json` | watched projects, their last activity and the Claude sessions open in them |
| `lapsed.json` | projects whose watch lapsed, which a comment from you restarts |
| `secrets.json` (0600) | per-project webhook secret and webhook GID |
| `history.json` | per-task run timestamps (rate cap) and last wake time (sweep) |
| `queue/` | events waiting for the worker |

## Troubleshooting

- **Nothing happens on a comment:** `status` first: is the project watched and the listener
  up? Then `webhook.log`. `IGNORED` means not watched (and not lapsed, or not your comment on a bot task); `SESSION` lines show sessions starting and closing a watch, `REWATCH` a lapsed one restarted. No `EVENTS` line means Asana isn't
  reaching the listener; run `list` for `last_failure_at`, and `tailscale funnel status`.
- **Nothing happens on a task the bot handed back to you:** it is assigned to you, not
  DevBot. @-mention DevBot in the comment, or assign the task to DevBot.
- **`REJECT ... bad signature`:** the stored secret doesn't match. `unregister`, then watch again.
- **Run exits non-zero:** read its `runs/` log.

## Billing

Runs drop `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN` from their environment. `sync.py`
loads `studio/.env`, which carries an API key for the Hermes collectors, and a key in the
environment outranks the claude.ai login: the first live run, 17 November 2026, billed API
credits until this was fixed. A bot branch in a repo with the client-data guard installed is
checked against the denylist when its run ends, since runs commit with hooks off; a hit goes
to Slack.
