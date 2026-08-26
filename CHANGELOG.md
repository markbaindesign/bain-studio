# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
- The AI search readiness tool now detects skills and expertise signals (BSTD-769).
- Looper artifacts moved from `studio/looper` to `docs/looper` (SL-122), and looper
  progress notes now record full file paths (SL-123).
- This changelog realigned to Keep a Changelog 1.1.0, with an `[Unreleased]` section
  and version link definitions.
- Upwork withdrawal fee analysis moved to Dropbox and indexed in the knowledge base (SL-127).
- `studio/looper-test` mirror files are no longer versioned.

### Fixed
- Looper misread re-queued tasks as having no new instructions, so re-queued work was
  silently skipped.
- ADR 013 and the email DNS setup doc corrected - the records are now published and
  verified, and the missing SPF/DMARC was reclassified as a regression rather than a
  gap that had never been configured (SL-129).
- Documentation audit across `docs/` corrected infrastructure claims that no longer
  matched reality (BSTD-774).

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

[Unreleased]: https://github.com/markbaindesign/bain-studio/compare/1.1.0...develop
[1.1.0]: https://github.com/markbaindesign/bain-studio/compare/1.0.1...1.1.0
[1.0.1]: https://github.com/markbaindesign/bain-studio/compare/1.0.0...1.0.1
[1.0.0]: https://github.com/markbaindesign/bain-studio/releases/tag/1.0.0
