---
tags: [utility, ops, asana, agents]
god: hermes
command: python3 studio/asana_webhook.py {serve|register|unregister|list|catchup}
description: Asana webhook listener that wakes a project's headless Claude agent when Mark or PmBot comments on, assigns, or adds a DevBot task - instead of waiting for someone to open a session
---

# Asana webhook listener

Project agents used to see Asana activity only when a session was started by hand. This listener
receives Asana webhooks and launches `claude -p` in the matching project folder. Decision record:
[ADR 025](../adr/025-asana-webhooks-wake-project-agents.md).

```
Asana ──HTTPS──> Tailscale Funnel ──> 127.0.0.1:$ASANA_WEBHOOK_PORT/asana/{PREFIX}
                                         │  verify X-Hook-Signature, drop irrelevant events,
                                         │  write a queue file, return 200 (< 10 s)
                                         ▼
                                      worker thread
                                         │  fetch story/task from the API, debounce 20 s,
                                         │  skip if a Claude session is open in the project,
                                         │  cap 3 runs per task per hour
                                         ▼
                              claude -p  (cwd = project root)
```

## What wakes an agent

All three require the event to be authored by a user in `ASANA_WEBHOOK_TRIGGER_USERS`
(Mark and PmBot), and the task to be open and assigned to DevBot (`ASANA_BAINBOT_GID`):

| Event | Example |
|---|---|
| Comment added to a task | Mark replies on a mission task |
| Task assignee changed | PmBot reassigns a task to DevBot |
| Task added to the project | PmBot creates a task already assigned to DevBot |

Moving a task between sections (dragging it to DONE) does not wake anything.

Never: DevBot's own events (no self-triggering), system events, and **comments from anyone else,
including clients**. Asana text is untrusted data; a public endpoint must not let a client comment
start an agent with tools. Those comments are picked up at the project's next normal session.

## What the agent is told

A fixed prompt (`AGENT_PROMPT` in `studio/asana_webhook.py`): pull the project with
`sync.py --project {PREFIX}`, read the woken tasks in the mirror, do the work per the project's
`CLAUDE.md`, post a progress comment with `sync.py --comment`, exit. It must not push, merge,
deploy to production or send email, and asks in Asana when it needs a decision.

The run starts with `--restricted --strict-mcp-config`: no user, project or local settings
files and no MCP servers are loaded, so the explicit `--allowedTools` list (`ALLOWED`: file
tools, `sync.py`, local git up to commit) is the whole allow-list. Only `RUN_TOOLS` (`Read, Glob,
Grep, Edit, Write, Bash`) exist. The deny-list is the voice agent's `OUTWARD_TOOLS`, the whole
Asana MCP, `WebFetch` and `WebSearch`, plus `Edit` denies on the project's `.git/**`,
`.claude/**` and `.envrc`. Git hooks are switched off for the run
(`GIT_CONFIG_PARAMETERS='core.hooksPath=/dev/null'`), so a committed file can't execute. No
auto mode, and never `--dangerously-skip-permissions`. An agent that needs more (SSH, WP-CLI,
network, editing skills or `.claude/`) asks in Asana instead. Restricted mode does not load
`CLAUDE.md`, so the prompt tells the agent to read it first. See ADR 025 points 2 and 9. Model: `ASANA_WEBHOOK_MODEL`
(default `sonnet`). A project whose `.envrc` exports `CLAUDE_CONFIG_DIR` (KF) runs on that
account ([ADR 017](../adr/017-per-client-looper-queues.md)).

## One session per project

Before launching, the worker reads `~/.claude/sessions/*.json`, `~/.claude-kf/sessions/*.json`
and every live `claude` process's working directory, and skips the project if any of them is
inside the project root. That includes an idle interactive session left open in tmux. The activity stays pending, a
Slack ping says so once, and the run starts when the session closes. One run per project at a
time; runs are stopped after 60 minutes: SIGTERM to the whole process group, SIGKILL 30 seconds later if anything is left, so a hung run can never block its project. The listener rejects a request body over 1 MB (413) before reading it.

## Setup

Config in `studio/.env`:

```
ASANA_WEBHOOK_TRIGGER_USERS=<Mark GID>,<PmBot GID>
ASANA_WEBHOOK_URL=https://<machine>.<tailnet>.ts.net/asana
ASANA_WEBHOOK_PORT=8787
ASANA_WEBHOOK_PROJECTS=BSTD
```

Rollout: BSTD only (also the code default) until the end-to-end and reboot tests pass, then add BD.

1. Expose the listener: `tailscale funnel --bg --set-path /asana http://127.0.0.1:8787`
2. Install and start the services (they run from the ops worktree, [ADR 014](../adr/014-ops-worktree-for-scheduled-jobs.md)):
   ```
   cp studio/scripts/systemd/asana-webhook* ~/.config/systemd/user/
   systemctl --user daemon-reload
   systemctl --user enable --now asana-webhook.service asana-webhook-catchup.timer
   ```
   User lingering must be on (`loginctl show-user $USER -p Linger`) for it to start at boot.
3. Register each project: `python3 studio/asana_webhook.py register --project BSTD`.
   The listener must already be live: Asana sends the `X-Hook-Secret` handshake *during* the
   registration call, and the listener only accepts a handshake for 2 minutes after `register`
   arms it, so nobody else can plant a secret.

## Adding a project

1. Add its prefix to `ASANA_WEBHOOK_PROJECTS` (it must be in the studio registry with an
   `ASANA_PROJECT_GID` in its `CLAUDE.md`).
2. `systemctl --user restart asana-webhook`
3. `python3 studio/asana_webhook.py register --project {PREFIX}`

## Daily catch-up

`asana-webhook-catchup.timer` runs `catchup` at 07:45. Per project it re-registers a webhook that
Asana has deactivated or deleted (Asana deletes one after 24 hours of failed deliveries), but only
for a project registered before: one with no stored `webhook_gid` is logged and skipped, so first
registration is always a manual `register`. It then
queues any open DevBot task whose latest Mark/PmBot comment is newer than both DevBot's latest
comment and the last time the listener woke an agent for it.

## Files

State lives outside the repo, under `$XDG_STATE_HOME/bain-studio/asana-webhook/`
(default `~/.local/state/...`):

| Path | Holds |
|---|---|
| `webhook.log` | every handshake, rejection, queue, deferral, launch and exit |
| `runs/{PREFIX}-{stamp}.log` | full output of each agent run |
| `secrets.json` (0600) | per-project webhook secret and webhook GID |
| `history.json` | per-task run timestamps (rate cap) and last wake time (catch-up) |
| `queue/` | events waiting for the worker |

## Troubleshooting

- **Nothing happens on a comment:** check `webhook.log`. No `EVENTS` line means Asana isn't
  reaching the listener; run `list` to see `last_failure_at`, and `tailscale funnel status`.
  `DEFERRED` means a session is open in the project.
- **`REJECT ... bad signature`:** the stored secret doesn't match. `unregister` then `register`.
- **Run exits non-zero:** read its `runs/` log.
