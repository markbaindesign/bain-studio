---
tags:
- reference
- cheatsheet
description: Quick reference for all studio skills, shell scripts, and Python utilities
---

# Studio Cheatsheet

Quick reference for every tool in the studio toolbox.

---

## Skills

Invoke in Claude Code with `/skill-name [args]`.

### Studio Routines

| Skill | Invoke | What it does |
|-------|--------|--------------|
| `studio-startup` | `/studio-startup` | Morning sync + Abderus sweep + financial pulse |
| `studio-shutdown` | `/studio-shutdown` | End-of-session retro, commit check, blocker flag |
| `studio-delivery-gate` | `/studio-delivery-gate` | Themis QA → Mark sign-off → Iris → invoice → harvest |
| `studio-ghost-projects` | `/studio-ghost-projects` | Scan for inactive/stale registered projects |
| `studio-pm-align` | `/studio-pm-align` | Align a project's Asana board with studio template |
| `abderus` | `/abderus` | Timing sweep: harvest gaps, overdue tasks, stale triage |
| `task-looper` | `/task-looper` | Work through BainBot Asana tasks in a loop |
| `check-inbox` | `/check-inbox` | Process messages in `.claude/inbox/` |

### Project Lifecycle

| Skill | Invoke | What it does |
|-------|--------|--------------|
| `triage` | `/triage` | Classify an inbound signal; route to pursue/decline/hold |
| `athena` | `/athena` | Qualify brief, research client, estimate, draft proposal |
| `erichthonius` | `/erichthonius [brief]` | Estimate hours using Mnemosyne comps |
| `plutus` | `/plutus` | Margin check and tax review on any proposal |
| `nike` | `/nike` | Write or refine a proposal or scope doc |
| `commission` | `/commission` | Commission an approved spec — scaffold + Asana create |
| `register-project` | `/register-project` | Add a project to projects.json + CLAUDE.md |
| `scaffold-dir` | `/scaffold-dir` | Create project directory + git init |
| `seed-tasks` | `/seed-tasks` | Create initial tasks in Asana via bainbot API |
| `studio-delivery-gate` | `/studio-delivery-gate` | Full delivery sequence |
| `poros` | `/poros [project]` | Raise an invoice for a project milestone |
| `log-project` | `/log-project` | Interview + append row to project-database.csv |
| `harvest` | `/harvest [project]` | Generate case study, blog post, testimonial request |

### Context Switching

| Skill | Invoke | What it does |
|-------|--------|--------------|
| `focus` | `/focus MCF` | Mid-day context switch — runs recap from studio dir |
| `recap` | `/recap` | Re-entry brief for the current project directory |
| `project-status` | `/project-status` | View or set project status in projects.json |
| `onboard-audit` | `/onboard-audit` | Audit all active projects against onboarding checklist |

### Content & Copy

| Skill | Invoke | What it does |
|-------|--------|--------------|
| `copywriter` | `/copywriter` | Studio voice review + copy editing |
| `company-brief` | `/company-brief` | Draft a company brief for a client |
| `review-spec` | `/review-spec` | Gate review for spec candidates |
| `nurture` | `/nurture` | Triage spec nursery drafts (pursue/defer/discard) |
| `internal-project-seed` | `/internal-project-seed` | Interview → structured brief for an internal project idea |
| `web-researcher` | `/web-researcher [query]` | Search and summarise external info |
| `grill-me` | `/grill-me` | Relentless interview to stress-test a plan or design |
| `brand-doc` | `/brand-doc file.md` | Convert Markdown → Bain Design branded PDF |

### QA & Delivery

| Skill | Invoke | What it does |
|-------|--------|--------------|
| `themis` | `/themis` | Full QA: scope, accessibility, performance |
| `eunomia` | `/eunomia` | Scope compliance check only |
| `dike` | `/dike` | WCAG 2.1 AA accessibility check only |
| `eirene` | `/eirene` | Core Web Vitals + performance check only |

### Social & Presence

| Skill | Invoke | What it does |
|-------|--------|--------------|
| `iris` | `/iris` | Studio social presence — watches for moments to broadcast |
| `arke` | `/arke` | Event spotting — scan for shareable moments |
| `aura` | `/aura [moment]` | Draft a social post |
| `kairos` | `/kairos` | Schedule a drafted post for optimal timing |

### Finance

| Skill | Invoke | What it does |
|-------|--------|--------------|
| `plutus` | `/plutus` | Margin check + tax awareness + invoicing |
| `penia` | `/penia` | 90-day cashflow projection |
| `euporia` | `/euporia` | Quarterly tax prep (Mod 303 IVA, Mod 130 IRPF) |
| `harvest-notes` | `/harvest-notes` | Harvest tagged ideas from Obsidian daily notes |

### Setup & Config

| Skill | Invoke | What it does |
|-------|--------|--------------|
| `bootstrap-claude` | `/bootstrap-claude` | Bootstrap a new Claude project with default config |
| `default-perms` | `/default-perms` | Write default permissions to `.claude/settings.json` |

### WordPress

| Skill | Invoke | What it does |
|-------|--------|--------------|
| `hephaestus` | `/hephaestus` | WordPress/PHP/React build planning and architecture |
| `caeculus` | `/caeculus` | Frontend architecture for React/Next.js |
| `periphetes` | `/periphetes` | DevOps: Cloudways, DNS, SSL, redirects, DDEV |
| `wp-css-override` | `/wp-css-override` | CSS override patterns for WordPress |
| `wp-plugin-expert` | `/wp-plugin-expert` | WordPress plugin deep knowledge |

### Design

| Skill | Invoke | What it does |
|-------|--------|--------------|
| `aphrodite` | `/aphrodite` | Visual design direction + brand review |
| `anteros` | `/anteros` | Brand compliance review |
| `harmonia` | `/harmonia` | Layout architecture: grid, spacing, typography |
| `pallas` | `/pallas [client/sector]` | Research a client, sector, or technology |

---

## Shell Scripts (`~/bin/`)

| Script | Usage | What it does |
|--------|-------|--------------|
| `studio-open` | `studio-open MCF` | Open a project by prefix in new Terminator tab |
| `studio-tabs` | `studio-tabs` | Open all active projects as Terminator tabs |
| `open-project` | `open-project /path/to/project` | 2-pane Terminator tab: zsh left, claude right |
| `brand-doc` | `brand-doc input.md [output.pdf]` | Convert Markdown to Bain Design branded PDF |
| `process-notes` | `process-notes` | Clean raw Obsidian notes with Claude, move to processed/ |
| `project-health` | `project-health` | Check health of registered studio projects |
| `wp` | `wp ...` | WP-CLI (WordPress command line) |
| `composer` | `composer ...` | PHP Composer package manager |

---

## Studio Python Scripts (`studio/`)

| Script | Run | What it does |
|--------|-----|--------------|
| `sync.py` | `python3 studio/sync.py` | Pull all Asana mirrors + push local edits to Asana |
| `sync.py --setup` | `python3 studio/sync.py --setup --project MCF` | First-time custom field setup for a project |
| `sync.py --create` | `python3 studio/sync.py --create --name "Name" --prefix MCF --path /path` | Scaffold new Asana project from template |
| `notifier.py` | `python3 studio/notifier.py "msg" --priority high --sender hermes` | Send a Slack notification |
| `postman.py` | `python3 studio/postman.py` | Process `.claude/inbox/` message queue |
| `dashboard/server.py` | `python3 studio/dashboard/server.py` | Launch studio dashboard at localhost:5555 |
| `collectors/gnucash_collector.py` | `python3 studio/collectors/gnucash_collector.py` | Parse GnuCash → context/finance/accounts.json |
| `collectors/harvest_kf_collector.py` | `python3 studio/collectors/harvest_kf_collector.py` | Fetch KF Harvest hours → time_snapshot.json |
| `collectors/obsidian_collector.py` | `python3 studio/collectors/obsidian_collector.py` | Harvest ideas/stubs from Obsidian notes |

---

## Key Files

| File | Purpose |
|------|---------|
| `studio/projects.json` | Registered project registry (path + status) |
| `studio/projects.md` | Human-readable registry table (auto-generated by sync) |
| `studio/.env` | API tokens: ASANA_PAT, HARVEST_*, SLACK_WEBHOOK_URL, STUDIO_CONTENT_DIR |
| `.claude/asana-mirror.md` | Local Asana task mirror for this project |
| `.claude/inbox/` | Inter-agent message inbox |
| `.claude/open-questions.md` | Unresolved open questions for this project |
| `context/finance/accounts.json` | GnuCash financial snapshot (written by collector) |
| `context/projects/kf/time_snapshot.json` | KF Harvest time budget snapshot |
