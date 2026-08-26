# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/markbaindesign/bain-studio/compare/1.3.0...develop
[1.3.0]: https://github.com/markbaindesign/bain-studio/compare/1.2.0...1.3.0
[1.2.0]: https://github.com/markbaindesign/bain-studio/compare/1.1.0...1.2.0
[1.1.0]: https://github.com/markbaindesign/bain-studio/compare/1.0.1...1.1.0
[1.0.1]: https://github.com/markbaindesign/bain-studio/compare/1.0.0...1.0.1
[1.0.0]: https://github.com/markbaindesign/bain-studio/releases/tag/1.0.0
