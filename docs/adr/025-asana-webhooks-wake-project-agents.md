---
tags: [adr, agents, asana, infrastructure, security]
god: hermes
description: Project agents are woken by Asana webhooks through Tailscale Funnel rather than by polling. Only Mark and PmBot can trigger a run, a project with an open Claude session is never given a second one, and runs are permission-checked rather than unrestricted.
---

# ADR 025 — Asana webhooks wake project agents

Date: 2026-10-22
Status: Proposed
Related: [ADR 003](003-multi-agent-studio-architecture.md) (revisits its "autonomous trigger"
condition), [ADR 014](014-ops-worktree-for-scheduled-jobs.md),
[ADR 017](017-per-client-looper-queues.md), [ADR 021](021-studio-state-and-registry-leave-the-repo.md)

## Context

Agents saw Asana activity only when someone started a session. A reply from Mark on a mission
task sat unread until he opened a terminal for that project, which defeats the point of
handing the task to DevBot.

ADR 003 deferred autonomous agents and said to revisit when agents "need to run autonomously on
a schedule or trigger each other without human intervention". This is that case, for one narrow
trigger. Mark chose webhooks over cron polling: Hermes' polling budget (60 min minimum) is too
slow for a conversation, and too costly to tighten.

## Decision

A listener on the dev machine (`studio/asana_webhook.py`, systemd user service run from the ops
worktree) receives Asana webhooks through Tailscale Funnel and launches `claude -p` in the
matching project folder.

1. **Only Mark and PmBot trigger runs.** The brief proposed "anyone except DevBot". Clients
   comment on these boards, Asana text is untrusted (bain-studio `CLAUDE.md`), and the endpoint
   is public. A client comment therefore never starts an agent; it waits for a normal session.
2. **Explicit allow-list.** Runs get `--allowedTools` for file tools, `sync.py`, and local git
   (status, diff, log, branch, add, commit, feature start), plus a deny-list (outward tools, the
   whole Asana MCP, push/merge). No auto mode and never `--dangerously-skip-permissions`, which
   the looper uses for queue work Mark started himself. Anything else the project's own
   settings don't allow is denied, and the agent asks in Asana.
3. **One session per project, including interactive ones.** The guard reads the Claude session
   registry and live `claude` processes' working directories, not a listener-private lock, so a
   tmux session left open on a project blocks a headless run there. The looper's state-file guard was not reused because it only sees looper
   runs.
4. **Fast acknowledgement.** The HTTP handler verifies the signature, filters, queues and returns.
   API lookups and launches happen in a worker thread, well clear of Asana's 10 second limit.
5. **Handshake only when armed.** The listener accepts an `X-Hook-Secret` handshake only within
   2 minutes of `register` for that project, so a stranger cannot register their own secret.
6. **Loop cap.** At most 3 runs per task per hour. Filtering DevBot's own events stops
   self-triggering, but a PmBot to DevBot exchange could still ping-pong.
7. **Daily catch-up** re-registers dead webhooks and queues unanswered tasks, because Asana
   deletes a webhook after 24 hours of failed deliveries.
8. **State outside the repo**, under `$XDG_STATE_HOME/bain-studio/asana-webhook/`, in the
   direction ADR 021 sets.

## Consequences

- A comment from Mark or PmBot on a DevBot task gets a reply within about a minute, unless a
  session is open on that project, in which case it waits and Slack says so.
- Each wake is a full Claude run. Model defaults to Sonnet (ADR 003's guidance) and cost should
  be reviewed after the first weeks of use.
- The listener must be live before `register`, because Asana handshakes during the create call.
- The dev machine is now a public HTTPS endpoint for one path. It answers 401/403/404 to anything
  unsigned or unexpected.
- Client comments still need a person to start a session. Widening the trigger list is a
  deliberate decision for a later ADR, not a config tweak.
