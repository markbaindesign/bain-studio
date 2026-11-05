# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.22.0] - 2026-11-05

### Added
- **The Claude sessions dash is a pinned panel, not a terminal window.** `session-status --conky` prints the sessions once as conky markup and exits, feeding `~/.config/conky/studio-claude.conf` on the third monitor. The app used to run in a second Terminator window there, and getting back to the one holding the tmux sessions meant cycling *within* the app - `switch-windows` is disabled and `switch-applications` is `<Super>Tab`, which groups both windows under Terminator, and the launcher icon raised whichever it felt like. A dash is read, not typed into, so it stopped being a window: a dock with `SKIP_TASKBAR` and `SKIP_PAGER` that nothing can hand focus to.
- **The panel reserves the right quarter of that monitor.** A dock publishes `_NET_WM_STRUT_PARTIAL`, so a window maximized there fills the left 1440px and the panel is never covered. Measured with a probe window on each monitor: fullscreen is unaffected - struts constrain maximize, not fullscreen - and the other two monitors are untouched.
- **One card a session**, three lines each, on a rounded Tokyo Night surface with the status colour as a bar down the left edge. 480px is about 51 characters, which a table does not fit. Three lines rather than four because the card's height decides how many sessions the column holds - 13 against 10, where 12 sessions have been seen running at once. Anything past the thirteenth is counted on a `+N more` line, never dropped.
- **Account usage as bars.** Under each account's quota line, one bar for the five-hour window and one for the week, each filled to its percentage with a marker where the budget says it should be by now. Ported from the studio dashboard's usage card, which is where the pace idea comes from. A window whose reset has already passed gets no bar, for the same reason the text says `reset` rather than quoting a figure from a window that is gone.
- **`studio/claude_pace.py`**, holding the quota budget rules in one place: 20% a work day for the week with weekends budgeting nothing, 20% an hour for the five-hour window, amber 5 points over the budgeted figure and red 15. They were JavaScript in `dashboard.html`; `server.py` now serves `five_pace` and `weekly_pace` from the module, the page renders what it is sent, and its two functions are gone. The port was differential-tested against the JavaScript on 40 randomised cases before that code was deleted - no disagreement in `expected` or `state`.
- **A level floor the dashboard did not have.** `colour_state` reports red at 90% of a window however well paced it is. Pace alone shows green at 95% on a Friday afternoon, because spending the last of the week on the last day is exactly on budget - which is the moment the warning is most wanted.

### Changed
- **The dashboard's Claude usage card reads its pace from the server** rather than computing it in the page, so the dashboard and the session dash cannot drift apart on what counts as burning too fast.

### Fixed
- **The dash no longer blocks maximizing the whole third monitor by accident.** It briefly ran as a `normal` window after "it prevents apps going fullscreen" was taken at face value, which turned out to be the wrong diagnosis: struts constrain maximize, and the reservation is wanted. The numbers are in `docs/utilities/session-status.md` rather than anyone's memory.

### Notes for the next person
Four dead ends are recorded in `docs/utilities/session-status.md`, all of which present as "nothing is drawing":
- conky draws Imlib2 `${image}` **after** the text, so a background PNG covers every row. `lua_draw_hook_pre` is the only layer behind it, and it needs `conky-all`, not `conky-std` - both have Lua, only `conky-all` ships the cairo binding.
- `CAIRO_OPERATOR_SOURCE` is **unbounded**: it paints the whole clip region rather than the path, so rounded corners come out square. The default `OVER` is bounded and keeps the source alpha anyway.
- `${goto}` measures from the **window** edge, not the text area, so a card's body lines slide under its status bar unless they repeat the inner margin.
- Check any of it with `gnome-screenshot`, never `import -window root`: under mutter the root window does not reliably hold what is on screen for a translucent window, and it produced two wrong diagnoses.

## [1.21.0] - 2026-11-05

### Added
- **Studio looper's concurrency guard states the all-clear** instead of saying nothing. `looper_logic.py concurrency` now prints `CLEAR:no other session targets {PREFIX}` when nothing competes, and names the runner (`- launched by runner {id}`) when `LOOPER_RUN_ID` is set. Silence was too weak a signal: on the night of 5 November a headless iteration read empty output as "the guard is broken", went looking at processes, found `looper_runner.py` holding `/tmp/studio-looper/runner.lock` along with its own `claude -p` child, concluded a rival run held the queue, and refused to start. Nothing was wrong - the runner holds that lock for the whole window by design and had launched the very session that then read it as a competitor. The window ended after 1 of 6 tasks. Step 1a is now explicit that this script's output is the only concurrency signal, with one scoped exception for an interactive run, where a live lock pid genuinely does mean a nightly window is in progress and the session should ask Mark rather than decide alone.
- **`looper_logic.py live-tasks {PREFIX}`**, printing each live session's `current_task` one per line, for Step 2's orphan recovery.
- **The looper runner tells an early stop from a drained queue.** It infers progress from `~/logs/task-looper.log` growing, so a session that declines to start looked exactly like an empty queue. It now records why the loop exited and counts tasks still at Looper Status `Queue`: a no-progress exit with work remaining logs `ENDED EARLY` and notifies at high priority, while the quota-deadline and iteration-cap exits report work carried over, at normal priority. Last night's early stop would have paged rather than passing unnoticed until the morning.

### Fixed
- **Orphan recovery read the wrong field and could reset a live task.** Step 2 built its set of in-flight tasks with `concurrency | grep '^LIVE:' | cut -d: -f5`, but the deadline on that line is an ISO timestamp whose own colons shift every later field - on a state file holding `current_task: SL-042`, `-f5` returns `00`. The live set was therefore always wrong, so `find_orphans` could class a genuinely in-flight task as unclaimed and reset it to `Queue`. Latent while Step 2 only runs after Step 1a finds no live file, but one interactive run alongside the nightly window reaches it. Step 2 calls `live-tasks` instead, and the skill now says why those lines must never be field-split.
- **The looper runner no longer risks dying silently on import.** It loads `looper_logic` relative to its own directory rather than to `STUDIO`, which resolves to the dev checkout even under the ops deploy - a `STUDIO`-relative import would pull the module from whichever branch dev happened to have checked out, and on one lacking `window_summary` that is an `ImportError` at module scope, before `notify()` exists. The window would be lost in silence, which is the failure this release was written to end. `looper_runner.py` also gains `from __future__ import annotations`, without which the new helper's `list[str]` annotation is a `TypeError` on this box's Python 3.8.
- **The studio-looper behavioural eval no longer fails on correct refusals.** `test_concurrency_live_blocks_second_run` accepted only the phrases "already running" and "not starting a second", and failed on refusals worded "The run did not start. Another session already holds the SLT queue" and "Not starting the run. The concurrency guard reports a live SLT run". It failed the same way against unmodified skill text, so this was long-standing flakiness rather than a regression, and it cost real debugging time deciding which. `reports_refusal()` matches any of the usual wordings; breadth is safe because the structural assertions in the same eval - the live file still present, no second state file created - are what prove the run never started.

## [1.20.0] - 2026-11-04

### Added
- **Session status** gains a column legend above the rows, naming each column. It is laid out by the same code as the rows, so it names only the columns that fit and breaks where they break at any width.

### Changed
- **Session status** calls the CLI's `busy` status `working`, in a muted green. The rename happens at display time: the CLI still emits `busy`, so the `shell` detection that depends on its word is untouched.
- **Session status** sorts waiting, shell, idle, working. Working moved to the bottom because a session mid-turn is asking for nothing, while a parked one may be waiting to be picked up - which is also why idle is now orange, and no longer dimmed, since dim turned the orange brown. Within every group the most recently active session is at the top rather than the longest-standing one.
- **Copywriter** is an agent (`.claude/agents/copywriter.md`) rather than a skill holding an abbreviated copy of the voice rules; the skill becomes a convenience trigger pointing at it. One definition of the voice instead of a skill-sized summary drifting from the master document.
- **Four PM skills load again.** `pm-asana-sync`, `pm-onboard`, `pm-retro` and `pm-todos` existed only in the stale `skills/` directory, which was shadowed by `.claude/skills/`, and were therefore unloadable. Two of them want review against current practice: `pm-asana-sync` runs `sync.py` after mirror edits, and `pm-todos` writes task state to `TODO.md` alongside the Asana mirror.

### Fixed
- **Studio docs and skills point at the project ledger.** ADR-007 retired `context/portfolio/project-database.csv` on 2026-07-15 in favour of one Markdown file per project under `context/portfolio/projects/`, read through `pipeline/project_db.py`. Fifteen files still named the CSV, so `/harvest` and others were reading a path that no longer exists. The references are rewritten rather than repointed, since the data model changed too: rows became project files, columns became frontmatter fields, and the skills that load the ledger now go through `project_db.load_all()`.

### Removed
- The stale `skills/` directory, a June copy of the skill set shadowed by the actively maintained `.claude/skills/`. Eight of its thirteen entries were duplicates, `interview-brief` now lives in `bain-skills`, and `skills/athena` was a symlink.

## [1.19.0] - 2026-10-30

### Added
- **Repo status** (`studio/scripts/repo-status`, tmux window `repos`): one screen showing every registered project's repo and what is unfinished in it - uncommitted changes, commits that exist only on this machine, branches not merged into the integration branch, extra worktrees - sorted so whatever is holding unfinished work sits at the top. The companion to session status: that one answers which session needs attention, this one answers where work was left. Nothing is fetched, so "behind" is not shown at all; without a fetch it would be a stale number dressed as a fact. See `docs/utilities/repo-status.md`.
- **Repo status** counts three kinds of change apart: files Mark edited, the `asana-mirror.md` and `asana-ids.json` that `sync.py` rewrites on a schedule, and untracked `.claude/` and `.ddev/` directories that will never be committed. Counted together, ten of nineteen repos sat permanently at the top of the list, which is the same as sorting by nothing. A repo with nothing modified but its mirror gets its own state below "ahead".
- **Repo status** reports ops drift on its second line: which tag the ops worktree holds, whether a newer one exists, and whether it has local changes that would stop `ops-deploy.sh`. A tagged release is not done until ops is running it (ADR 014).
- **Session status** gains a quota header: each Claude account's five-hour and weekly rate limit, with the time each resets. Dim until 70%, amber there, red at 90%, taking whichever window of whichever account is worst. A window whose reset has already passed reports "reset" rather than quoting a percentage from a window that has gone.
- **Session status** gains a model column and a context percentage per session, joined to each row by session id. Model choice is the largest lever on quota, so it earns a column. Both come from the files the status line already writes, so there are still no hooks and no database.

## [1.18.0] - 2026-10-30

### Added
- **Session status** reads each session's transcript, in the same pass that gives it a timestamp, and shows two new columns: the context the session is holding (the figure Claude Code prints in its own footer) and the session's AI title, so a row says what the session is working on and not only that it is working.
- **Session status:** a `shell` status. The CLI reports `busy` for as long as a background shell lives on, which hid finished turns among live ones. A session whose newest transcript entry is an assistant message that ended its turn with nothing outstanding is reported as `shell` - neither working nor parked, because the shell may yet wake it.

### Changed
- **Session status** sorts waiting, shell, busy, idle. A session sitting on a permission prompt or holding a finished turn is asking for something, so it comes above live work; idle sits last, since a session parked for two days is asking for nothing.
- **Session status** moves to say what it is doing without being read: busy spins, the statuses that want a human pulse, idle is greyed out, and the cursor stays hidden until a key is pressed.
- **Session status** names accounts after the signed-in email domain, so the column reads `bain` and `kf` - the same names the status line shows - instead of naming the config directory `main`.

### Fixed
- **Sync:** a registry entry whose directory no longer exists said "no CLAUDE.md found", which reads as a repo that is present but unconfigured. It now reports the missing path, so the fix (drop the entry from `projects.json`) is obvious.

## [1.17.0] - 2026-10-30

### Changed
- **Session status** now covers every Claude account on the machine. `claude agents --json` reports only the config directory it is invoked with, so sessions running under a second account (KF, under `CLAUDE_CONFIG_DIR=~/.claude-kf`) were missing from the list with nothing to say so - 10 shown against 12 running. Every `~/.claude*` directory holding a `projects/` folder is now queried. An account column appears once more than one account has sessions.
- **Session status** setup points the always-on `sessions` tmux window at the ops worktree rather than the development checkout, matching the `monitor` window. The pane must be respawned after a deploy to pick up a new version.

### Removed
- **Session status:** jump-to-pane on `enter`. `tmux switch-client` moves whichever client the app is running in, which with several clients attached is not reliably the one in front of you. The tmux target is displayed instead and the session is found by hand.

## [1.16.0] - 2026-10-30

### Added
- **Raise invoice** (`studio/tools/raise-invoice/raise_invoice.py`): reports projects with unbilled Harvest hours and creates Harvest draft invoices, either from a project's uninvoiced time or as a fixed milestone line. Drafts only - it never sends - and it refuses to create one without an explicit client type, so IVA and IRPF treatment is always deliberate. See `docs/utilities/raise-invoice.md`.
- **LinkedIn posting** (`studio/linkedin_post.py`, `/linkedin-post`): publishes an approved post to Mark's LinkedIn profile. Dry run by default, with a lint pass for m-dashes, length and hashtag count. Kairos hands off to it once Mark approves. See `docs/utilities/linkedin-post.md`.
- **Session status** (`studio/scripts/session-status`): a dense list of every Claude Code session on the machine, which tmux pane it is in, and whether it needs attention, sorted needs-me-first. Reads `claude agents --json`, with no hooks and no database. See `docs/utilities/session-status.md`.
- **Postman ping:** `send()` now alerts the live Claude session(s) working in the receiving project: tmux bell, a 📬 prefix on the window name, a message flashed on attached tmux clients, and a desktop notification. New `postman.py unmark` clears the marker. See `docs/gods/hermes/postman.md`.
- **`inbox-alert.py` hook:** lists unread postman mail in Claude's context on each prompt and at session start, and clears the 📬 marker once the inbox is empty.
- **ADR 022** - Asana tasks carry their own context: subtasks are only for the steps of a task that fits in one sitting; anything larger, and any feedback item, is a top-level task.
- **ADR 023** - contact form bot protection via Cloudflare Turnstile, with the Hephaestus checklist for wiring it into Contact Form 7.
- **ADR 024** - cutover hostname sweep.
- Registered four projects: ASP (Algolia Search Plugin), JBP (Beato Properties), LRET (Lead Retriever) and TIS.

### Changed
- **`/raise-invoice` now drives Harvest** instead of producing an invoice document by hand. Harvest owns the numbering, the PDF, sending and payment tracking; the skill is a thin trigger for the script.

### Fixed
- **Postman:** `--project` now resolves a registered prefix (e.g. `ASP`) through `docs/projects/*.md`. Before, only folder names matched, so KF's `ASP` messages fell back to `studio/inbox/` and sat unread.
- **Bitbucket SSH:** remotes use `ssh.bitbucket.org` (BSTD-834), and TARA is correctly recorded as a GitHub repo rather than Bitbucket.

## [1.15.1] - 2026-10-20

### Fixed
- **Sync:** a task in two normal projects no longer gets a new Local ID on every run. It keeps its ID while it is still in the project that owns that prefix (`assign_ids()`, `prefix_owners()`).
- **Templates:** `templates.json` pointed the internal project template at the SLW client project (`1215208138819356`); it now points at `{TEMPLATE Project}` (`1211611158088242`). `ASANA_TEMPLATE_PROJECT_GID` in `studio/.env` (untracked) was corrected to match.

## [1.15.0] - 2026-10-08

### Added
- **Income forecast** (`studio/dashboard/income_forecast.py`): forecast income in five tiers (receivable, unbilled, fixed, predicted, milestone), configured in `FINANCE_CONFIG_DIR/income.yaml` and merged into `accounts.json` `upcoming_all`, so every cash flow forecast includes income. See `docs/utilities/income-forecast.md`.
- Dashboard **Cashflow** screen: every bank account's projected daily balance on one EUR chart, with a base case / with upside toggle and shortfall highlighting. Shares `studio/dashboard/cashflow.py` with the daily Slack forecast, so the two agree.
- Dashboard **Configs** screen: the finance YAML configs rendered read-only.
- Every Financial screen shows the USD and GBP to EUR exchange rates in use and their source, in red when the live rate fetch failed (new `/api/fx` endpoint).

### Changed
- `account_forecast_report.py` reads income from the income forecast instead of its own hard-coded recurring income.
- `/account-forecast` refuses to present outgoings-only balances and reports a base case and a with-upside projection.

### Fixed
- Dashboard Outstanding Invoices treated every invoice as EUR. USD and GBP invoices now show their own currency with the EUR value, and the receivable total is summed in EUR.

## [1.14.0] - 2026-10-06

### Added
- `sync.py --create-task --task-assignee me` assigns the new task to Mark (`ASANA_USER_GID`), so it lands in his My Tasks.

### Fixed
- `sync.py --create-task` ignored `--task-assignee` and `--task-depends-on`: every task went to BainBot and dependencies were silently dropped. Both now reach Asana, the mirror entry records the real assignee and the task it blocks, and a failed dependency link exits 1 instead of passing. The default assignee is still BainBot.

## [1.13.1] - 2026-10-06

### Fixed
- `ops-deploy.sh` no longer reports a conflict on `studio/sync.log`. `sync.py` rotates that log, and rotation replaced the ops symlink with a real file, so the sync log is no longer linked: cron's copy lives in the ops worktree.
- Test runs no longer write fake entries into the real `studio/sync.log`. `sync.py` takes a `SYNC_LOG` path override, which the test suite points at a temp file.

## [1.13.0] - 2026-10-06

### Added
- **Voice agent** (`studio/voice/`, `/voice-agent`): a hands-free spoken front desk on the OpenAI Realtime API. It hands studio work to background `claude -p` sessions (up to 3 at once, per-project by prefix), reads results back, and blocks outward actions (sending, pushing, merging, sharing) until Mark gives a spoken yes. Transcripts are saved to Dropbox. See `docs/utilities/voice-agent.md`.
- **studio-tmux** (`studio/scripts/studio-tmux`): opens or reattaches to a `studio` tmux session with one window per studio area, configured in `~/.config/bain-studio/tmux.json`. See `docs/utilities/studio-tmux.md`.
- ivas-prep `upwork_check.py`: flags Upwork clients paid in the quarter who have no matching Harvest invoice, and warns when the Upwork report ends before quarter end.
- ivas-prep `issue_date.py`: reads an invoice's issue date from its PDF (English, Spanish and Catalan labels).

### Changed
- `/open` opens a project as a window in the studio tmux session instead of a new Terminator tab.
- ivas-prep files Gmail invoices into the quarter of their issue date, not the quarter being searched, and flags any that belong to an earlier quarter.
- ivas-prep skill uses absolute paths so it works when invoked outside bain-studio; VIES validation PDFs go in `Vendes/` under a fixed naming convention.
- Mod 130 profit base: the comment on the `Pension` exclusion now records why it holds (voluntary UK National Insurance contributions, a personal cost). Behaviour is unchanged.

## [1.12.0] - 2026-10-02

### Added
- Studio dashboard Ops tab shows Tailscale and SSH status: backend state, this machine's tailnet name and IP, whether `ssh` is active, and a table of tailnet devices with online/offline and last-seen. Answers "can I reach this machine remotely".

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

[Unreleased]: https://github.com/markbaindesign/bain-studio/compare/1.20.0...develop
[1.20.0]: https://github.com/markbaindesign/bain-studio/compare/1.19.0...1.20.0
[1.19.0]: https://github.com/markbaindesign/bain-studio/compare/1.18.0...1.19.0
[1.18.0]: https://github.com/markbaindesign/bain-studio/compare/1.17.0...1.18.0
[1.17.0]: https://github.com/markbaindesign/bain-studio/compare/1.16.0...1.17.0
[1.16.0]: https://github.com/markbaindesign/bain-studio/compare/1.15.1...1.16.0
[1.15.1]: https://github.com/markbaindesign/bain-studio/compare/1.15.0...1.15.1
[1.15.0]: https://github.com/markbaindesign/bain-studio/compare/1.14.0...1.15.0
[1.14.0]: https://github.com/markbaindesign/bain-studio/compare/1.13.1...1.14.0
[1.13.1]: https://github.com/markbaindesign/bain-studio/compare/1.13.0...1.13.1
[1.13.0]: https://github.com/markbaindesign/bain-studio/compare/1.12.0...1.13.0
[1.12.0]: https://github.com/markbaindesign/bain-studio/compare/1.11.2...1.12.0
[1.11.2]: https://github.com/markbaindesign/bain-studio/compare/1.11.1...1.11.2
[1.11.1]: https://github.com/markbaindesign/bain-studio/compare/1.11.0...1.11.1
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
