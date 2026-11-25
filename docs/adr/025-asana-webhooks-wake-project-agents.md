---
tags: [adr, agents, asana, infrastructure, security]
god: hermes
description: Project agents are woken by Asana webhooks through Tailscale Funnel rather than by polling. Only Mark and PmBot can trigger a run, a project with an open Claude session is never given a second one, and runs are permission-checked rather than unrestricted.
---

# ADR 025 — Asana webhooks wake project agents

Date: 2026-10-22
Status: Accepted, amended 2026-11-17 and 2026-11-25 (see the addenda)
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
2. **Explicit allow-list, and nothing inherited.** Runs start with `--restricted
   --strict-mcp-config`, so user, project and local settings files and MCP servers are not
   loaded: `--allowedTools` is the *whole* allow-list, not an addition to the project's own.
   (Without this, BSTD's local settings would add `python3 *` and BD's `Bash(*)`, and every
   user settings file adds `WebFetch`/`WebSearch`: open egress for a run that reads Asana
   comments.) Only `Read, Glob, Grep, Edit, Write, Bash` exist (`--tools`); the allow-list is
   file tools, `sync.py`, and local git (status, diff, log, branch, add, commit, feature start).
   The deny-list adds outward tools, the whole Asana MCP, `WebFetch`, `WebSearch` and git flow
   publish. No auto mode and never `--dangerously-skip-permissions`, which the looper uses for
   queue work Mark started himself. Anything else is denied, and the agent asks in Asana.
   Because the project's `CLAUDE.md` is not loaded in restricted mode, the prompt tells the
   agent to read it first.
9. **A run cannot plant code that runs later.** File writes plus `git commit` would let a run
   write a git hook that the commit then executes, or edit settings and `.envrc` for the next
   run. Restricted mode already refuses writes to git and settings files; the run also gets
   explicit `Edit(//<root>/.git/**)`, `.claude/**` and `.envrc` denies, and
   `GIT_CONFIG_PARAMETERS='core.hooksPath=/dev/null'` so no hook runs at all. (Git here is
   2.25, which predates `GIT_CONFIG_COUNT`.) The run can still post any text as an Asana comment, so
   credential files in the project (`.env`, `wp-config.php`, ...) get `Read` denies too. Cost: a webhook run cannot edit skills, settings
   or archive `.claude/inbox/`; that work waits for a normal session.
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
   deletes a webhook after 24 hours of failed deliveries. It only repairs a webhook that was
   registered before (a stored `webhook_gid`); first registration is always a manual
   `register`, so listing a project in `ASANA_WEBHOOK_PROJECTS` never goes live by itself.
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

## Addendum 2026-11-17: watched projects, per-task worktrees, Opus

Tested once on 2026-10-22 and never deployed. The one live event was held back by rule 3: Mark
had a session open on the project, which is exactly when he wants an answer. He works
interactively, hands tasks to DevBot and comments on them, and wants replies while he works.
Decided with Mark in a grill session:

- **Rule 3 is replaced.** Runs no longer wait for open sessions. Each task's run gets its own
  git worktree outside the project (`bot-worktrees/{PREFIX}/{LOCAL-ID}`, branch
  `bot/{LOCAL-ID}` from `develop`), may edit only there, and is denied every edit in the
  project checkout. An answer leaves nothing behind; work stays on its branch for review.
- **Opt-in watching.** Only watched projects get runs (`/project-watcher PREFIX`, or
  `asana_webhook.py watch`). Watching stops 30 minutes after Mark's or PmBot's last activity on
  the project's bot tasks, once its runs finish, with a Slack line. `ASANA_WEBHOOK_PROJECTS` is
  gone: any registered project can be watched, and watching registers its webhook.
- **The daily catch-up only repairs webhooks.** It no longer queues runs, so an unwatched
  project gets no unannounced session. `watch` does the unanswered-comment sweep instead.
- **Limits:** one run per task at a time (comments arriving meanwhile are batched into the next
  run), 2 per project, 3 in all, and the existing 3 per task per hour.
- **Model: Opus**, not Sonnet. Runs are on Mark's Max plan, not API credits, and volume is low;
  the cost is the shared usage window, which the limits above protect. A run that hits the
  limit posts nothing and Slack says so.
- **Replies always reach Mark.** A run posts one note at the end: `Answer:`, `Review:` or
  `Blocked:`. `sync.py` mentions Mark on those (and `Done:`) without the `@mark` token, and a
  `Review:` or `Done:` reassigns the task to him.
- **A handed-back task wakes the bot only when Mark @-mentions it.** After a `Review:` or
  `Done:` the task is his, and a plain comment from him is a note to himself or a client.
- **Runs read the registry and the project's Dropbox folder, read-only.** BSTD-841 stalled
  because a run could reach neither. Writes there stay with interactive sessions: a Dropbox
  edit has no branch and no review. Worktrees moved to `$XDG_DATA_HOME/bain-bot-worktrees/`
  so the registry folder can be denied to edits whole.

## Addendum 2026-11-19: a Claude session holds the watch (BSTD-894)

Watching only started when Mark remembered `/project-watcher`, and it lapsed after 30 quiet
minutes in Asana even while he was still working in the project. A comment after that was
logged `IGNORED` and dropped with no reply and no Slack line.

- **Opening a Claude session in a registered project watches it.** A `SessionStart` hook
  (`asana_webhook.py session-start`) maps the session's directory to the deepest registered
  project root and records the session. Starting a watch, which may register the webhook and
  runs the sweep, is left to the listener's worker so the hook stays fast. It is async, prints
  nothing and always exits 0.
- **An open session holds the watch.** The watch ends 30 minutes after the last session in
  the project closes or Mark's last activity, whichever is later. `SessionEnd` records the
  close. Because it does not fire on a crash or kill, the worker also checks each recorded
  Claude pid in `/proc` and treats a session that has gone as closing then.
- **A lapsed watch restarts on Mark's comment.** When a watch lapses the project goes into
  `lapsed.json`. A later comment from Mark (not PmBot) on a bot task there watches the
  project again, queues that task and says so on Slack. It does not sweep. `unwatch` is a
  deliberate stop and clears the lapse, so its comments stay ignored, as do comments on
  projects never watched.
- **Bot sessions never start or extend a watch.** Webhook runs carry `BAIN_BOT_RUN=1`, looper
  sessions carry `LOOPER_RUN_ID`, and any session in a bot worktree is skipped. Runs use
  `--restricted` and load no hooks anyway; this does not depend on that.
- **Hooks are installed by script, not by hand:** `studio/scripts/install-watch-hooks.py
  --apply`, run from the checkout the listener runs from, covering `~/.claude` and
  `~/.claude-kf`.

## Addendum 2026-11-25: a second worktree for a factory product (BSTD-905)

A run could edit only its own worktree of the project repo. The theme factory keeps each
product in a separate repo, so a run on a factory task could decide but never build: on BTF-105
it had to answer `Blocked:` instead of making the change Mark had chosen.

**Decision:** when the project has a `products.json` and the task's Related Milestone names an
`in-production` product, the run also gets a worktree of that product's repo, on its bot branch,
with `Edit` and git `status/diff/log/show/add/commit` (via `git -C`) allowed there and nothing
else widened. The product's main checkout and graduated products stay denied. `products.json`
is read from the main checkout, never the run's worktree, so a run cannot widen its own next
run. Covered by `studio/tests/test_asana_webhook.py`.

## Addendum 2026-11-19: nightly sweep of unwatched projects (BSTD-895)

Opt-in watching left a gap: a comment on a bot task in a project nobody watched waited for a
session, or for the looper if the task happened to be queued in SL. The addendum above made the
daily catch-up start nothing, so that an unwatched project got no unannounced session. That
stays true of `catchup`; a separate, scheduled `nightly` command now closes the gap.

- **Same triggers and limits as the listener.** Assignment to the bot, an unanswered comment on
  a bot task, and an @-mention of the bot on a handed-back task. Each run is launched by the
  listener's own `Worker._launch`, so it gets the same worktree, permissions, closing comment
  and per-task rate limit.
- **Bounded.** Only triggers from the last 7 days, at most 6 runs a night, watched projects
  skipped (they are the listener's), and tasks the looper has queued skipped (Looper Status
  `Queue` or `In Progress`, read from Asana, not the SL mirror).
- **Never alongside the looper.** It runs at 07:15, after the 02:00 window's 5-hour ceiling,
  waits while the runner's lock is held by a live process, and stops launching if a window
  starts. It reads the lock and never takes it: the runner exits when it finds the lock held.
