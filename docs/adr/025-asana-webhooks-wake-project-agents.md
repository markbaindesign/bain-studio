---
tags: [adr, agents, asana, infrastructure, security]
god: hermes
description: Project agents are woken by Asana webhooks through Tailscale Funnel rather than by polling. Only Mark and PmBot can trigger a run, a project with an open Claude session is never given a second one, and runs are permission-checked rather than unrestricted.
---

# ADR 025 — Asana webhooks wake project agents

Date: 2026-10-22
Status: Accepted, amended 2026-11-17 (see the addendum)
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

## Addendum 2026-11-19: runs execute code inside the OS sandbox (BSTD-896)

Runs could edit but not run anything, so code they delivered was untested (BSTD-841). Allowing
`python3` through the permission rules alone would not be safe: rules match the command string,
so `Bash(python3 *)` lets `python3 x.py` read `studio/.env`, write to Dropbox and reach the
network.

**Findings, Claude Code 2.1.328 on this machine (bubblewrap 0.12, git 2.25):**

- The sandbox works with `claude -p`, `--restricted` and our `--allowedTools` rules. `--settings`
  still applies under `--restricted`, so the run's sandbox config is passed there.
- **It needs `socat` as well as `bwrap`, and socat is not installed here.** Without it Claude
  Code prints a warning and runs every command **unsandboxed**, even with
  `allowUnsandboxedCommands: false`. Only `sandbox.failIfUnavailable: true` makes it refuse to
  start instead.
- With socat present: writes are confined to the working directory, the network is closed
  (`allowedDomains: []` denies without prompting under `-p`, raw sockets included), and a
  script cannot write the main checkout's `.git`, so it cannot delete branches.
- **Permission `Read()` denies are not enforced inside the sandbox**: a script read
  `studio/.env` and the Claude credentials. They must be repeated as
  `sandbox.filesystem.denyRead`, which does hide them (`~` and `**/` globs work; a denied
  directory such as `~/.ssh` appears empty).
- **`--add-dir` folders are writable inside the sandbox.** The registry and Dropbox need
  `sandbox.filesystem.denyWrite`.
- **The run inherited the listener's environment, and with it every `studio/.env` key** (the
  listener imports `sync.py`, which loads them): Asana, Harvest, Cloudways, Slack and more.
  Harmless while a run could execute nothing; readable by any script once it can. Runs now get
  `run_env()`, which drops every key `studio/.env` defines and anything named like a credential.
- Inside the sandbox the worktree's `.git` and `.claude/` are already unwritable, but `.envrc`
  is not; all three are added to `denyWrite` for the project and the worktree.
- `git add`/`commit` fail inside it (the worktree's git dir is in the read-only main checkout,
  and the sandbox's own mount points show up as untracked files), and `sync.py` needs `.env`
  and Asana. They run outside it via `excludedCommands`, which only exempts a command already
  allowed by a rule.

**Decision.** `_launch` turns on execution only when `bwrap` and `socat` are both on the run's
PATH. It then passes `sandbox_settings()` (fail-closed, no network, secret files and home
credentials hidden, the listener's state dir hidden, read-only dirs unwritable, git and the two
sync.py calls excluded) and adds `exec_allow_rules()`: `python3`, `pytest`, and the project's
own test command from a `BOT_TEST_COMMAND:` line in its `CLAUDE.md`. Otherwise the allow rules
stay as they were and the prompt tells the run its change is untested. The listener logs
`SANDBOX-OFF` on each such launch. `studio/scripts/sandbox_probe.py` is the live test: it runs
one real run with the real flags and environment and checks 30 escape attempts and
capabilities from outside (`--read-only-dir` points it at the real Dropbox folder).

**Consequence.** Until `sudo apt install socat` is run on the listener's machine, nothing
changes. After it, runs can test their own work. A user-local socat on `~/.local/bin` would
also enable it, which is why the probe takes `--path-prefix` instead.
