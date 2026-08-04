# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

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
