# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.11.2] - 2026-10-02

### Fixed
- `sync.py` logs Asana's error message alongside HTTP failures (e.g. `403 ... | Asana: You do not have access to this project.`), so bare 400/403 lines in `sync.log` say why.

## [1.11.1] - 2026-10-02

### Fixed
- Daily Brief only surfaces tasks assigned to Mark (`ASANA_USER_GID`); tasks assigned to BainBot, other people or nobody are no longer chased.

## [1.11.0] - 2026-10-01

### Changed
- **Daily Brief severity now comes from the age of the problem, never from how long the finding
  has been reported.** Ageing on the list used to promote findings a level at a time, all the way
  to `critical`, which emptied the word of meaning: on 2026-09-30 the brief carried 58 criticals
  and 57 of them had been put there by the escalation clock rather than by a check. Since every
  check already derives severity from the thing's own age, that clock was also counting age twice.
  `ESCALATE_AFTER_DAYS` is gone, `apply_escalation` is now `stamp_first_seen` and only records when
  a finding was first raised. Same day's data re-run: 1 critical instead of 50.
- **Today is ranked by severity, then acute before chronic, then the age of the problem, then how
  long it has been reported.** Previously a newly raised critical could never reach Today, because
  findings raised earlier outranked it regardless of how bad they were. Ranking on age alone then
  had the opposite flaw: a cron job that failed on its last run has an age of zero, so live
  breakage sorted below a task 476 days overdue. Findings that represent something erroring right
  now are marked `acute=True` (failing cron job, repeated transcription failure, crashed check,
  unreadable GnuCash book or finance snapshot) and sort above chronic ones of equal severity.
- **Checks that had no age rule got one**: untouched tasks and their per-project rollup go `high`
  past 180 days (`UNTOUCHED_HIGH_DAYS`), a silent active project past 90 (`PROJECT_STALE_HIGH_DAYS`),
  and a quiet cron job once it has missed 3 of its own cycles (`QUIET_CYCLES_HIGH`) rather than
  staying `normal` however long it has been dead. `report.py`, silent for 89 days, was `normal`.
- **An untriaged voice note is `normal` until 7 days**, not 3 (`VOICE_NOTE_STALE_DAYS`).

### Added
- **Daily Brief flags open tasks untouched for 60+ days** (`UNTOUCHED_AFTER_DAYS`), rolled up into
  one summary per project past 5 (`UNTOUCHED_ROLLUP`). Nothing previously caught a task that had
  no due date, was not blocked and was not in review, so a dropped task could sit indefinitely.
  Found while investigating two Algolia suspension warnings that sat unread in Asana for 12 weeks
  until the applications were deleted.

### Removed
- **The Daily Brief no longer reports finance tasks that are merely due soon.** The brief is a
  safety net for work that has been missed; a task on schedule has not been missed and Asana
  already shows it. A routine invoice due that day was being ranked `critical`.

### Documentation
- MWE (Middle Way Education) registered in the project table and `docs/projects/`. ADR 021, studio
  state and the registry leave the repo.

## [1.10.1] - 2026-10-01

### Fixed
- **algolia-pulse docs said "indices" where they meant "apps".** Per Algolia's own support
  documentation, free-plan inactivity is measured per application, not per index, so one query
  against a single index keeps the whole app alive. The skill, its `SKILL.md` and
  `docs/utilities/algolia-pulse.md` all described it as keeping individual indices alive, which
  would suggest every index needs its own config entry. Also records that local apps are the ones
  most at risk, since they get no traffic. Docs only; no behaviour change. (Originally drafted as
  1.9.1; renumbered because 1.10.0 had already shipped.)

## [1.10.0] - 2026-10-01

### Added
- **Studio dashboard Highlights tab** is the new home page: a ranked act/watch/info list drawn from
  the other tabs (missed scheduled jobs, BBVA shortfall, overdue invoices, payments due within 7
  days, uninvoiced time, KF pace, high-score briefs).
- **Claude usage on the dashboard**, weekly and 5-hour, each with a pace check (weekly budgets 20%
  per work day, Mon-Fri; the 5-hour window is straight-line). `~/.claude/hooks/statusline.py` now
  also writes `weekly_pct` and `weekly_reset_ts` to `ratelimit-current.json`.
- **Dashboard Ops tab** compares every crontab entry with its log file and flags missed runs,
  with per-job log links. Built after a late boot silently skipped the 08:xx collectors.
- **`studio/scripts/dashboard-app.sh`** opens the dashboard as a standalone Chromium app window,
  starting the server if needed. `docs/utilities/studio-dashboard.md`.
- **ga-report** draws charts, excludes `(not set)`, and writes into the client folder.
- **brand-doc** reflows wrapped text and list items and numbers pages "N of M".
- **bb-pr** reads Bitbucket credentials from `studio/.env`.

### Documentation
- ADR 019 (code projects use a standalone staging app, Proposed), Obsidian-on-Linux
  troubleshooting entry, corrected Dropbox and project-database paths, refreshed project notes.

## [1.9.0] - 2026-09-29

### Added
- **`sync.py --create-subtask`** adds subtasks under an existing Asana task via bainbot, in the order
  given, and prints their GIDs (`--task-gid` with repeatable `--subtask-name`). Tests and
  `docs/utilities/new-subtask.md`.
- **algolia-pulse refuses a config file that group or others can read** (it holds live API keys) and
  posts a Slack alert on any config error, so a broken weekly cron does not fail unseen.
- **Bookkeeper tooling fixes** from the 2026-09-23 catch-up: date filter on import,
  `add-rule --replace`, `check-rules`, all account types in `accounts`, BBVA value-date and
  acknowledged-duplicate dedupe, and a profile-mismatch warning. Harvest invoices are split into
  IVA/IRPF, and Stripe and PayPal are no longer treated as feeds.

### Fixed
- **The task mirror lost tasks in any Asana project over 100 tasks.** `fetch_tasks` read only the
  first page; it now paginates.
- **Follower add/remove flip-flop.** Set-field pushes now update the in-memory task, so the rebuilt
  mirror stops writing the pre-push followers back. Removed tasks are logged by ID.
- **A newly assigned Local ID could collide with an adopted one.** `assign_ids` now moves the counter
  past every ID already in use for the prefix before assigning any.

## [1.8.0] - 2026-09-29

### Changed
- **The tracked `.claude/settings.json` now holds project policy only** (`defaultMode`, the `deny`
  list, `disabledMcpjsonServers`, generic tool allowances). Machine-specific permissions - absolute
  `Edit(//...)` paths, `additionalDirectories`, MCP approvals - live in the gitignored
  `.claude/settings.local.json`. A tracked file that differed per machine made
  `ops-deploy.sh` refuse to deploy, and leaked local paths into a public repo.
  `Bash(*)` is no longer allowed by the tracked file.
- `CLAUDE.md` documents the rule, including never approving a command that embeds a credential
  (the approval string is stored in plaintext).

## [1.7.0] - 2026-09-29

### Added
- **algolia-pulse posts a Slack summary after every real run.** One message via the studio
  notifier: a low-priority `N/N indices OK` line with a per-app breakdown, or a high-priority
  alert listing each failed index. `--no-notify` skips it; `--dry-run` never posts.
- **`docs/utilities/algolia-pulse.md`**, the tool's utility note, and a Claude usage optimization
  guide under `docs/utilities/`.

### Changed
- **algolia-pulse now runs weekly** (Mondays 07:00) instead of daily. SKILL.md and the utility
  note describe the weekly schedule and note that a search-only key can be used in the
  `admin_api_key` field.

## [1.6.3] - 2026-09-29

### Fixed
- **algolia-pulse broke on the algoliasearch v4 SDK.** v4 removed the `algoliasearch.search_client`
  module the script imported, so every pulse run (including the daily cron) failed with an import
  error. The script now uses the v4 client and search call.

## [1.6.2] - 2026-09-17

### Fixed
- **ops-deploy.sh aborted any deploy spanning more than 20 commits** (exit 141, before checking
  anything out). The change list piped `git log` into `head -20`; `head` closing the pipe
  SIGPIPEd `git`, and `set -o pipefail` turned that into a failure. The limit is now `git log -20`.

## [1.6.1] - 2026-09-17

### Fixed
- **The ops worktree would have kept its own copy of the Daily Brief and audio notes state.**
  `ops-worktree-link.sh` did not list `daily_brief_state.json` or `audio_notes_state.json`, so
  cron runs would have re-transcribed every recording already done from the dev checkout and
  restarted escalation ages from zero. Both state files and both logs are now linked.

## [1.6.0] - 2026-09-17

### Added
- **Daily Brief** (`studio/collectors/daily_brief.py`) - a morning chief-of-staff sweep of
  finance (books behind, account shortfalls, tax deadlines, losses, money tasks), operations
  (failing or quiet cron jobs, stale snapshot, uncommitted work, unmerged branches), projects
  (overdue, blocked on Mark, stuck in review, stale), clients (chases gone quiet) and voice
  notes. Writes a ranked note to `Work Notes/Daily Brief/`, escalates findings ignored for a
  week, and posts the top items to Slack. No Claude call.
- **Audio notes** (`studio/collectors/audio_notes.py`) - transcribes voice memos recorded in the
  Obsidian vault. The checklist line above each embedded recording is the memo's context, so a
  memo recorded under a task item is linked to that task. Silent recordings are skipped and
  reported; audio is never moved (that would break the embed).
- `sync.py --get-task <url|gid|LOCAL-ID>` - read-only lookup of any Asana task via bainbot, so
  the looper can follow links to other tasks instead of blocking on them.
- `studio/scripts/rename_prefix.py` - renames a project's task ID prefix while keeping every
  task number (used for PIPE -> UAP).
- `sync.py --update-task`, for task notes the mirror cannot push.
- **bookkeeper** - catches the GnuCash book up from bank feeds (Wise API, BBVA/Upwork/Stripe
  CSV and XLSX, Harvest invoices), with journal and amend commands.
- **scaffold-dir** - WordPress-aware project scaffolding: pinned core, `--db`, a generated
  install script and a three-tier `.gitignore`.
- ADR 016 (WordPress factory consolidation), ADR 017 (per-client looper queues), ADR 018
  (uptime monitoring via Better Stack, email and Slack only).

### Changed
- **Studio inbox**: the Hermes postman sweep posts each message to Slack once and stamps it
  `notified_at` instead of archiving it, and `/check-inbox` now also reads `studio/inbox/`.
  Messages from other sessions (e.g. the KF account) were previously archived before any
  session saw them. New message type `note`.
- **studio-looper**: a documented-answer gate - before blocking on a question the looper checks
  the task, CLAUDE.md files and ADRs, and works title-only tasks with one clear reading.
- The Upwork Pipeline's task prefix is now UAP (was PIPE); references updated.
- brand-doc: tighter body leading in branded PDFs.

## [1.5.1] - 2026-09-02

### Fixed
- **wise-pulse crashed writing its baseline checkpoint**, so the file never existed and
  every run was a first run - no change was ever detected. `save_checkpoint` unpacked
  `fetch_balances`' `(balance_obj, amount, currency)` triples as pairs.

### Added
- `studio/tests/test_wise_pulse.py` - covers the checkpoint round-trip and the seam
  between `fetch_balances`' output shape and everything downstream. Three bugs shipped
  in this script because nothing exercised its non-network half.

## [1.5.0] - 2026-09-02

### Fixed
- **The daily payment forecast attributed nothing billed to Wise Business (EUR).**
  `ACCOUNT_LABEL_MAP` in `account_forecast_report.py` covered BBVA and the Wise USD/GBP
  balances but not the EUR one, so every transaction naming that account in
  `recurring-transactions.yaml` - Asana and Claude among them - fell through to the
  report's unassigned list each morning instead of being forecast against a balance.
- **wise-pulse could not have notified from cron.** Its Slack call shelled out to a
  nested subprocess with `cwd` hardcoded to the dev checkout, which the release-pinned
  ops worktree is not. It also passed `--channel finance`, absent from `notifier.py`'s
  `choices`: argparse would have exited non-zero, the notify call would have reported
  failure, and the checkpoint would never have advanced past the first change - the same
  delta re-reported every morning indefinitely. Now imports `notify` in-process against
  a derived studio path.

### Changed
- The forecast report's unassigned section reads "no matching account balance" rather
  than "no account attributed". The transactions did carry an account; what was missing
  was a balance to match it against.

### Added
- `docs/utilities/wise-pulse.md`, missing since the skill shipped in 1.4.0.

## [1.4.0] - 2026-08-27

### Added
- `wise-pulse` skill - polls the six tracked Wise balances daily, detects movement, and
  Slacks the deltas for manual booking in GnuCash. Interim measure until Wise banking
  transaction feeds are enabled (BSTD-775).
- `algolia-pulse` skill - keeps free-tier Algolia indices alive (BSTD-781).
- Queue count in studio-looper's completion and blocking logs (BSTD-047).
- ADR 014 - scheduled jobs run from a release-pinned ops worktree.

## [1.3.0] - 2026-08-26

### Added
- `studio/scripts/ops-deploy.sh` - deploys a release tag to the ops worktree that cron
  runs from. Fetches, verifies the tag, refuses to run over local modifications rather
  than discarding them, checks out detached, re-runs the link script, and prints the
  rollback command. `--check` reports what would change in either direction, so a
  rollback lists what it removes instead of an empty forward range.
- `STUDIO_DIR` in `studio/.env`, naming where the studio repo lives.

### Changed
- **The ops worktree now sits on a detached HEAD at a release tag, not on `main`.**
  Pinning it to `main` broke git flow entirely: `git flow release finish` runs
  `git checkout main || die`, and a branch can only be checked out in one worktree at a
  time. Detaching frees `main` and pins cron to an explicit named version, making
  rollback a one-liner.
- **All 10 scheduled jobs now run from the ops worktree.** `looper_runner` was previously
  excluded on the mistaken grounds that it creates branches and commits; it does neither.
  It only launches a claude session, and branching happens inside that session in each
  task's own home project. The exclusion had left the one unattended 02:00 job as the
  only thing still executing whatever branch happened to be checked out.
- `looper_runner` derives the studio path instead of hardcoding it: `STUDIO_DIR`, then the
  registry, then its own repo root, with each candidate validated. A stale or mistyped
  value falls through rather than being trusted, and total failure raises with the paths
  tried instead of pointing a looper session somewhere wrong.

## [1.2.0] - 2026-08-26

### Added
- **Ops worktree.** Scheduled jobs now run from a separate git worktree pinned to `main`
  (`/home/bain/ops/bain-studio`) rather than from the dev checkout. A cron entry names a
  path, not a ref, so with one checkout cron ran whatever branch happened to be checked
  out - meaning dev branch state silently decided what production ops did. Code now
  reaches cron by being merged, which is deliberate. See `docs/utilities/ops-worktree.md`.
- `studio/scripts/ops-worktree-link.sh` symlinks the 27 gitignored runtime paths (secrets,
  collector state, Asana mirrors, inbox, logs) from the ops worktree back to the dev
  checkout, so there is exactly one copy of each. Sharing state is a correctness
  requirement: duplicated state would make `wp_pulse` re-summarise posts it had already
  digested and `gmail_watch` reprocess threads.

### Fixed
- **Recurring bills are forecast from the most recent actual billing period, not a
  full-history average.** Averaging understated every cost whose price had risen, and the
  shortfall warnings built on those figures inherited the error - Autonomos forecast at
  380.12 against an actual 380.88, Movistar at 104.16 against 119.77. Forecast entries now
  carry an `amount_basis` field showing what the figure was derived from.
- Adds Mod 130 estimation: 20% of cumulative net business profit for the year to date, less
  Mod 130 already paid.

## [1.1.0] - 2026-08-26

### Added
- **WP Pulse** (`studio/collectors/wp_pulse.py`) - collates new posts across 13 WordPress
  development blogs into a single summarised markdown digest, written to the Obsidian
  vault twice weekly with a Slack ping. Each post gets a short summary and a relevance
  note written against the studio's actual stack.
- **HTML to Markdown tool** (`studio/html_to_markdown.py`) - converts web pages into
  agent-readable markdown (BSTD-770).
- ACF Local JSON sync in `setup-wp.sh`, so new WordPress scaffolds import field groups
  into the database rather than leaving a deployed JSON file silently unsynced.
- Studio Looper is now a documented project (`docs/projects/sl.md`), with its
  cross-project queue rules written down.
- Guidance for verifying scheduled collectors under cron's own environment, after a
  `PATH` gap was found leaving every `claude`-invoking collector failing silently.

### Changed
- **This repo is now scoped to tools only.** Audits, investigations, research and
  analysis no longer belong here - they go to `$STUDIO_CONTENT_DIR/research/`. The rule
  and its rationale are in "What belongs in this repo" in `CLAUDE.md`, and
  `docs/looper/`, `docs/research/` and `docs/audits/` are gitignored so the pattern
  cannot return.
- The `studio-looper` skill now decides whether a task needs a branch at all. Research
  output is written straight to Dropbox with no branch and no commit, and the Progress
  note names that path instead of a branch and commit.
- The AI search readiness tool now detects skills and expertise signals (BSTD-769).
- Looper progress notes now record full file paths (SL-123).
- This changelog realigned to Keep a Changelog 1.1.0, with an `[Unreleased]` section
  and version link definitions.
- `studio/looper-test` mirror files are no longer versioned.

### Removed
- Research and audit output that had accumulated under `docs/` (looper task reports,
  the Upwork withdrawal fee analysis, and personal expense notes). All of it is
  preserved in `$STUDIO_CONTENT_DIR/research/`; none of it was tool documentation.

### Fixed
- Looper misread re-queued tasks as having no new instructions, so re-queued work was
  silently skipped.
- ADR 013 and the email DNS setup doc corrected - the records are now published and
  verified, and the missing SPF/DMARC was reclassified as a regression rather than a
  gap that had never been configured (SL-129).
- Infrastructure claims across `docs/` corrected where they no longer matched reality
  (BSTD-774).

## [1.0.1] - 2026-08-04

### Fixed
- `ivas-prep`'s Gmail sender matching was broken by the public-repo PII scrub
  (real gestor/Movistar/Cloudways addresses were replaced with placeholders
  directly in the script). Real addresses now load from `studio/.env`
  (gitignored) via `IVAS_GESTOR_EMAIL` / `IVAS_MOVISTAR_FORWARD_EMAIL` /
  `IVAS_CLOUDWAYS_BILLING_EMAIL`, so the automation works again without any
  real address being committed.

## [1.0.0] - 2026-08-04

First tagged baseline of the studio's internal PM/ops system, built up over
207 commits with no prior release. High-level summary of what exists as of
this version:

### Added
- **Asana sync engine** (`studio/sync.py`, "Hermes") — bidirectional sync between local
  markdown mirrors and Asana, project registry, custom field setup, offline-first workflow.
- **Olympus multi-agent pantheon** — Athena (proposals/estimation), Hephaestus (technical
  build planning), Themis (QA/sign-off), Iris (social/announcements), Aphrodite (design
  review), Aura (SEO), Mnemosyne (project ledger/comps), and the rest of the household,
  each with a dedicated skill and doc entry.
- **Studio Looper** — cross-project task queue that works BainBot tasks from any studio
  project in Asana priority order, with git-flow-per-session branching and a nightly
  cron runner.
- **Studio Dashboard** — Flask app for finances (GnuCash) and time tracking (Harvest),
  with cashflow projection, account forecasting, and a daily Slack summary.
- **Upwork/LinkedIn proposal pipeline** — automated job scoring, skill-gap tracking,
  proposal generation, and a dedicated LinkedIn Asana project with its own status field.
- **Cloudways MCP hosting integration** — direct server/app management (deploy, backups,
  SSL, logs, env vars) from Claude Code, per ADR 006/012.
- **~90 slash-command skills** covering the full project lifecycle: triage → proposal →
  commission → build → QA → delivery → harvest, plus studio ops (onboarding, invoicing,
  tax prep, brand voice, portfolio, etc).

[Unreleased]: https://github.com/markbaindesign/bain-studio/compare/1.11.0...develop
[1.11.0]: https://github.com/markbaindesign/bain-studio/compare/1.10.1...1.11.0
[1.10.1]: https://github.com/markbaindesign/bain-studio/compare/1.10.0...1.10.1
[1.10.0]: https://github.com/markbaindesign/bain-studio/compare/1.9.0...1.10.0
[1.6.2]: https://github.com/markbaindesign/bain-studio/compare/1.6.1...1.6.2
[1.6.1]: https://github.com/markbaindesign/bain-studio/compare/1.6.0...1.6.1
[1.6.0]: https://github.com/markbaindesign/bain-studio/compare/1.5.1...1.6.0
[1.5.1]: https://github.com/markbaindesign/bain-studio/compare/1.5.0...1.5.1
[1.5.0]: https://github.com/markbaindesign/bain-studio/compare/1.4.0...1.5.0
[1.4.0]: https://github.com/markbaindesign/bain-studio/compare/1.3.0...1.4.0
[1.3.0]: https://github.com/markbaindesign/bain-studio/compare/1.2.0...1.3.0
[1.2.0]: https://github.com/markbaindesign/bain-studio/compare/1.1.0...1.2.0
[1.1.0]: https://github.com/markbaindesign/bain-studio/compare/1.0.1...1.1.0
[1.0.1]: https://github.com/markbaindesign/bain-studio/compare/1.0.0...1.0.1
[1.0.0]: https://github.com/markbaindesign/bain-studio/releases/tag/1.0.0
