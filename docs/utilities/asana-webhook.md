---
tags: [utility, ops, asana, agents]
god: hermes
command: python3 studio/asana_webhook.py {watch|unwatch|status|session-start|session-end|serve|register|unregister|list|catchup|nightly|inbox}
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
up with its sweep. The [nightly sweep](#nightly-sweep) also answers them if you never watch the project.

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

## Inbox poll: every project at once

```
python3 studio/asana_webhook.py inbox on       # poll every 3 minutes, from the listener
python3 studio/asana_webhook.py inbox off
python3 studio/asana_webhook.py inbox once     # one poll now
python3 studio/asana_webhook.py inbox          # on or off, and when it last ran
```

Asana has no API for a user's Inbox, so this is the substitute. While it is on, the listener
searches the workspace every 3 minutes for open tasks assigned to DevBot that changed since the
last poll (reaching back 10 minutes, because search lags behind writes), in **every** registered
project, watched or not and with or without a webhook. A task is queued when, inside that
window, Mark or PmBot commented with no DevBot reply since, or assigned it to DevBot (or created
it already assigned). Anything older was seen by an earlier poll, or predates switching it on,
so backlog tasks never wake in a burst. The first poll looks back one hour.

A task in SL or SLT is worked in its home project. A task whose project is not the root of its
own git repository is skipped. Queued tasks go through the same worker as webhook events: the
same run limits, rate cap, worktrees and permissions. The poll never expires: it runs until
switched off. Use it, or `watch`, not both for the same reason; they do not conflict.

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

- **A question or decision:** answer it, change nothing, and reply in plain words opening `@mark`, with no `Answer:` or `Reply:` label.
- **Work:** do it in the worktree, commit on `bot/{LOCAL-ID}`, post `Review: ...` with a `Check:` block.
- **Needs your call:** post `Blocked: ...` and stop.

Replies carry no path, branch, file name or URL: Mark does not read them and they bury the
point. Where he has to open something, such as a commit to review, it goes in a `Where:` block,
which goes at the foot of the same comment, below a blank line. An answer usually has none.

Answers, and `Review`, `Blocked` and `Done` notes, all mention you, so they reach the Mentioned
inbox and Slack. One comment per run, at the end. When the run exits, a worktree with no
commits and no changes is removed with its branch; one with work stays for you to review and
merge.

### Factory products: a second worktree

A factory project keeps each product in a repo of its own, listed in its `products.json`. When
the project has one and the task's **Related Milestone** names an `in-production` product (by
the codename in brackets, e.g. `Contents May Differ (prototype-hall)`), the run also gets a
worktree of that product's repo: `bain-bot-worktrees/{PREFIX}/{LOCAL-ID}--{codename}`, on the
same `bot/{LOCAL-ID}` branch name, from the product's `develop`. The prompt tells the run where
it is and to use `git -C <that path>` for it. When the run exits, each worktree is tidied on its
own: one with work stays, an untouched one goes.

`products.json` is read from the project's main checkout, never from the run's worktree, so a
run cannot promote a product for the next one. Graduated products, unknown codenames and a
`source` that is not a git repo root get no second worktree.

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
With a product worktree, the run additionally gets `--add-dir` and `Edit` on that worktree, and
git `status`, `diff`, `log`, `show`, `add`, `commit` there as `git -C <path> ...`; the product's
main checkout is denied for edits, and both carry the `.git`/`.claude`/`.envrc` edit denies and
the credential-file read denies. Nothing else widens.
A project whose `.envrc` exports `CLAUDE_CONFIG_DIR` (KF) runs on that account
([ADR 017](../adr/017-per-client-looper-queues.md)).

### Running code (sandbox)

When `bwrap` and `socat` are installed, runs may also run `python3`, `pytest` and the
project's test command (a `BOT_TEST_COMMAND: make test` line in its `CLAUDE.md`). Those run in
Claude Code's OS sandbox: no network, writes only in the run's worktree, and credential files
(`SECRET_FILES`, `~/.ssh`, `~/.claude/.credentials.json`, the listener's state dir) unreadable.
git and the two `sync.py` calls run outside it, still held to the rules above. The run's
environment never carries the listener's `studio/.env` keys (`run_env()`), sandbox or not. The sandbox is
fail-closed (`failIfUnavailable`): if it cannot start, the run does not start either.

Without socat (`sudo apt install socat`) Claude Code would otherwise run commands unsandboxed,
so the listener keeps the old rules, logs `SANDBOX-OFF {PREFIX} {ID}` and tells the run its
change is untested. Check the setup end to end with one short live run:

```bash
python3 studio/scripts/sandbox_probe.py               # exit 0 pass, 1 fail, 2 skipped (deps missing)
python3 studio/scripts/sandbox_probe.py --task BSTD-896   # also checks sync.py --get-task
python3 studio/scripts/sandbox_probe.py --read-only-dir /media/data/Dropbox/Work   # real Dropbox
```

Findings and the reasoning: [ADR 025](../adr/025-asana-webhooks-wake-project-agents.md),
2026-11-19 addendum.

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
   systemctl --user enable --now asana-webhook.service asana-webhook-catchup.timer \
     asana-webhook-nightly.timer
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

## Nightly sweep

A comment on a bot task in a project you are not watching would otherwise wait for a session
or the looper. `asana-webhook-nightly.timer` runs `nightly` at 07:15, after the 02:00 looper
window. It goes through every registered project that is not watched and has a git repository
of its own (so not SL or SLT), and starts a run for each task the listener would have woken
the bot on, had the project been watched:

- your or PmBot's newest comment on a task assigned to the bot, with no reply from the bot
  since and no run since;
- a task you assigned to the bot, with nothing from the bot since (an assignment by bainbot
  itself, from `sync.py --create-task`, does not count);
- on a handed-back task, a newest comment that @-mentions the bot.

Each run is exactly a listener run: its own worktree, one closing `Answer:`, `Review:` or
`Blocked:` comment, and the same limits (2 per project, 3 at once, 3 per task per hour,
1 hour each). On top of those:

| Rule | Why |
|---|---|
| Only triggers from the last 7 days count | an old thread is not revived |
| At most 6 runs a night; the rest wait for the next night, and Slack lists them | a backlog cannot use up the Max window |
| Tasks with Looper Status `Queue` or `In Progress` are skipped | they are the looper's |
| Never alongside the looper: it waits up to 2 hours while `/tmp/studio-looper/runner.lock` is held by a live process, and launches nothing more once a window starts | the two must not share the usage window or a repo. It only reads the lock: holding it would make the 02:00 runner exit |

See what it would do, without starting anything:

```
python3 studio/asana_webhook.py nightly --dry-run
```

## Files

State lives outside the repo, under `$XDG_STATE_HOME/bain-studio/asana-webhook/`:

| Path | Holds |
|---|---|
| `webhook.log` | handshakes, rejections, watch changes, queues, launches, exits |
| `runs/{PREFIX}-{LOCAL-ID}-{stamp}.log` | full output of each run |
| `watch.json` | watched projects, their last activity and the Claude sessions open in them |
| `lapsed.json` | projects whose watch lapsed, which a comment from you restarts |
| `inbox.json` | whether the inbox poll is on, and when it last ran |
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
