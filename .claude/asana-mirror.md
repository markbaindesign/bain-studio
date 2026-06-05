# Bot Asana Task Mirror
Last synced: 2026-06-05
Workspace GID: 512209774840
Assignee GID: 1209202434387214

## Bain Studio

### BSTD-005 — Replace ASANA_PAT with bainbot account token
- **Local ID:** BSTD-005
- **Asana ID:** 1215209467864880
- **Section:** NEXT UP
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214), Mark Bain (507443625075)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Generate from Asana as bainbot user at app.asana.com → My Settings → Apps → Personal Access Tokens
- **Blockers:** 2026-06-03 — Requires Mark to log into Asana as the bainbot account and generate a Personal Access Token at app.asana.com → My Settings → Apps → Personal Access Tokens. Once generated, add to studio/.env as ASANA_PAT.
- **Progress:** Checked 2026-06-03. Blocked — needs bainbot Asana credentials.
- **Comments:**
  > 2026-06-05 **Mark Bain:** Why is this needed? It has already been done I'm sure. More detail please!
- **Modified:** 2026-06-05T16:28:47
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209467864880

### BSTD-020 — Linked In job check - focus on new jobs
- **Local ID:** BSTD-020
- **Asana ID:** 1215230461939789
- **Section:** NEXT UP
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** Mark Bain (507443625075), BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Current linked in job check pipeline is surfacing jobs that are month or years old. These are likely no longer active. Check recent emails only. Nothing dated more than 3 months ago.
- **Blockers:** 2026-06-03 — Task has no notes. "LinkedIn job check — focus on new jobs" is ambiguous: could mean (a) scan LinkedIn Jobs for new freelance/contract postings matching studio skills, (b) monitor Mark's own profile/activity, or (c) something else entirely. Needs clarification from Mark: what specifically should be checked, how often, and what output is expected.
- **Progress:** Checked 2026-06-03. Blocked — ambiguous, needs Mark to add notes clarifying the intent.
- **Comments:**
  > 2026-06-03 **Mark Bain:** Note added.
  > 2026-06-05 **Mark Bain:** In the pipeline, there is a script that checks for linked in jobs that look interesting, but it surfaces very old roles that are out of date. I want to make sure the jobs are recent.
- **Modified:** 2026-06-05T16:31:02
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215230461939789

### BSTD-010 — Audit and complete studio dashboard
- **Local ID:** BSTD-010
- **Asana ID:** 1215209663490357
- **Section:** NEXT UP
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** studio/dashboard/ exists — assess current state, determine what data it surfaces, and complete or extend to show studio pulse: active projects, pipeline, cashflow, harvest status.
- **Blockers:** None identified.
- **Progress:** Checked 2026-06-03. Assessed: dashboard currently has Finance, KF time budget, and Pipeline tabs (1353-line dashboard.html). Missing: active projects tab and harvest status card. Both are buildable from existing data sources (projects.json/mirrors and project-database.csv). Deferred to dedicated branch: feature/bstd-010-dashboard-active-projects-harvest.
- **Comments:** none
- **Modified:** 2026-06-05T16:31:23
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209663490357

### BSTD-021 — Add API cost tracker to studio dashboard
- **Local ID:** BSTD-021
- **Asana ID:** 1215394379541907
- **Section:** NEXT UP
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Two parts: (1) log-scraping collector that aggregates total_cost_usd from hermes.log and any other Claude CLI invocations, writes to a costs.json snapshot; (2) new Dashboard tab or card surfacing per-agent cost breakdown + a direct link to console.anthropic.com for workspace billing totals. Blocked on rotating the leaked API key first.
- **Blockers:** 2026-06-03 — Task notes explicitly state: blocked on rotating the leaked API key first. Cannot proceed until the API key has been rotated and replaced in all .env files.
- **Progress:** Checked 2026-06-05.
- **Comments:** none
- **Modified:** 2026-06-05T16:29:30
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215394379541907

### BSTD-022 — Conduct a security audit on the studio project
- **Local ID:** BSTD-022
- **Asana ID:** 1215386521408712
- **Section:** NEXT UP
- **Due:** 2026-06-05
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** Mark Bain (507443625075), BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Investigate

    Are dangerous practices being used in the studio environment when using Claude?
    Is there a risk of contagion between projects? Is Claude restricted to certain files?
    Should Claude run in a VM rather than having access to the entire computer?
- **Blockers:** None identified.
- **Progress:** Checked 2026-06-05.
- **Comments:** none
- **Modified:** 2026-06-05T16:43:47
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215386521408712

### BSTD-012 — Backfill Mnemosyne (project-database.csv)
- **Local ID:** BSTD-012
- **Asana ID:** 1215209677034138
- **Section:** NEXT UP
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214), Mark Bain (507443625075)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** The studio project ledger is empty or sparse. Backfill completed projects using the log-project skill — client, sector, stack, estimate vs actuals, outcome grade, lessons. Mnemosyne grows wiser with every project entered.
- **Blockers:** 2026-06-03 — Cannot backfill without project data. Bainbot does not have knowledge of past project details (hours, prices, dates, outcomes). Mark must provide this data interactively via /log-project or by reviewing the workshop.md files in context/portfolio/. Bainbot can facilitate the interview but cannot generate the data.
- **Progress:** Checked 2026-06-03. Blocked — needs Mark to provide historical project data.
- **Comments:**
  > 2026-06-05 **Mark Bain:** What data is needed? Where should I provide it? Maybe work from a Google sheet? I can set this up, let me know
- **Modified:** 2026-06-05T16:32:02
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209677034138

### BSTD-019 — Fix VVV shutdown asking for password
- **Local ID:** BSTD-019
- **Asana ID:** 1215210721133744
- **Section:** NEXT UP
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** Mark Bain (507443625075), BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** No notes.
- **Blockers:** None identified.
- **Progress:** Checked 2026-06-05.
- **Comments:**
  > 2026-06-05 **Mark Bain:** How can I grant this? Does this mean we can't do it?
- **Modified:** 2026-06-05T16:29:15
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215210721133744

### BSTD-009 — Automate case study → website delivery pipeline
- **Local ID:** BSTD-009
- **Asana ID:** 1215209965255230
- **Section:** NEXT UP
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214), Mark Bain (507443625075)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Portfolio folder and workshop templates built. Wire up: workshop.md → generate upwork.md + website.md → screenshot assets → deliver to bain.design content/inbox. Screenshot script still needed (task #1 in session).
- **Blockers:** 2026-06-03 — Screenshot script not yet built; without it the pipeline cannot deliver visual assets. The workshop.md → upwork.md/website.md generation logic needs to be written (no existing script found). Scoping this as a multi-step build: (1) write a Python script that reads workshop.md and generates the two derivative files using templates; (2) integrate a screenshot tool (Playwright or puppeteer-based) for asset capture; (3) wire delivery to bain.design inbox. This is a standalone build task, not a blocker from outside.
- **Progress:** Checked 2026-06-03. Deferred — complex multi-step build, needs dedicated session.
- **Comments:**
  > 2026-06-05 **Mark Bain:** Agreed. This is a project stub not a task.
- **Modified:** 2026-06-05T16:33:26
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209965255230

### BSTD-023 — Create the studio brand voice
- **Local ID:** BSTD-023
- **Asana ID:** 1215445632997592
- **Section:** NEXT UP
- **Due:** 2026-06-08
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** Mark Bain (507443625075), BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** 1211312202132828 (1211312202132828), 1211859323827650 (1211859323827650), 1215445632997589 (1215445632997589), 1211859323827637 (1211859323827637)
- **Notes:** No notes.
- **Blockers:** None identified.
- **Progress:** Checked 2026-06-05.
- **Comments:** none
- **Modified:** 2026-06-05T16:43:39
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215445632997592


## DONE

### BSTD-013 — Set custom project icon on new Asana projects
- **Local ID:** BSTD-013
- **Asana ID:** 1215209467867245
- **Section:** DONE
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** After running sync.py --create, manually set the custom project icon in Asana — the API cannot copy it from the template.
- **Blockers:** None identified.
- **Progress:** Checked 2026-06-05.
- **Comments:** none
- **Modified:** 2026-06-05T16:03:02
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209467867245

### BSTD-011 — Build The Notifier
- **Local ID:** BSTD-011
- **Asana ID:** 1215209965001262
- **Section:** DONE
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Shared utility used by all gods to alert Mark at the three gates (proposal, delivery, financial) and for system events. Wire up Telegram bot via BotFather — token and chat ID into .env. Replace the rate-limit cron hack with a proper notification layer.
- **Blockers:** None identified.
- **Progress:** Checked 2026-06-05.
- **Comments:** none
- **Modified:** 2026-06-05T16:03:01
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209965001262

### BSTD-014 — Set up Telegram notifications for rate limit reset
- **Local ID:** BSTD-014
- **Asana ID:** 1215209394424148
- **Section:** DONE
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Create a Telegram bot via BotFather, get token and chat ID, then wire up cron job to send notifications when Claude API rate limit resets.
- **Blockers:** None identified.
- **Progress:** Checked 2026-06-05.
- **Comments:** none
- **Modified:** 2026-06-05T16:03:00
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209394424148

### BSTD-015 — Create the /studio-postman skill
- **Local ID:** BSTD-015
- **Asana ID:** 1215209677652051
- **Section:** DONE
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** Mark Bain (507443625075), BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** I need a way of passing data between projects. e.g. when using a studio skill, a project discovers a bug. So it wants to send a report to the studio. It could just copy a md report to an inbox, that's scanned on a schedule. Projects could have their own inbox.

Generally speaking how is communication going to happen outside the studio with mortal projects?

Projects are mortal because they are destined to die, unlike the studio which is eternal.
- **Blockers:** None identified.
- **Progress:** Checked 2026-06-05.
- **Comments:** none
- **Modified:** 2026-06-05T16:02:59
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209677652051

### BSTD-001 — Flesh out Iris skill
- **Local ID:** BSTD-001
- **Asana ID:** 1215209677218047
- **Section:** DONE
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Iris covers social media, event broadcasting, and studio presence. Skill folder exists but is a stub — define social post drafting, event announcements, and studio comms workflow.
- **Blockers:** None identified.
- **Progress:** Completed 2026-06-03. Full Iris skill built at ~/.claude/skills/iris/SKILL.md — defines Arke (event spotting), Aura (post writing), and Kairos (scheduling) sub-agents with signal/harvest/draft modes. Standalone Arke, Aura, and Kairos skills also created.
- **Comments:** none
- **Modified:** 2026-06-05T16:02:58
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209677218047

### BSTD-002 — Flesh out Themis skill
- **Local ID:** BSTD-002
- **Asana ID:** 1215209811194641
- **Section:** DONE
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Themis covers QA, sign-off, accessibility, scope compliance, and performance. Skill folder exists but is a stub — define QA checklist, delivery gate process, and sign-off workflow.
- **Blockers:** None identified.
- **Progress:** Completed 2026-06-03. Full Themis skill built at ~/.claude/skills/themis/SKILL.md — defines Eunomia (scope), Dike (accessibility/WCAG), and Eirene (Core Web Vitals) sub-agents with GATE CLEAR/BLOCKED ruling. Standalone sub-skills also created. Delivery gate workflow in studio-delivery-gate skill.
- **Comments:** none
- **Modified:** 2026-06-05T16:02:57
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209811194641

### BSTD-003 — Flesh out Hephaestus skill
- **Local ID:** BSTD-003
- **Asana ID:** 1215209663836183
- **Section:** DONE
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Hephaestus covers WordPress, PHP, React, Next.js, and infra. Skill folder exists but is a stub — define dev scoping, plugin/theme routing, and build handoff workflow.
- **Blockers:** None identified.
- **Progress:** Completed 2026-06-03. Full Hephaestus skill built at ~/.claude/skills/hephaestus/SKILL.md — plan and review modes covering Erichthonius (estimation), Caeculus (frontend/headless), and Periphetes (DevOps/infra). Standalone sub-skills also created.
- **Comments:** none
- **Modified:** 2026-06-05T16:02:57
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209663836183

### BSTD-004 — Flesh out Aphrodite skill
- **Local ID:** BSTD-004
- **Asana ID:** 1215209676329024
- **Section:** DONE
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Aphrodite covers visual design, UX, brand, and studio aesthetics. Skill folder exists but is a stub — define the full skill workflow: design direction, mood boards, brand review, handoff to Hephaestus.
- **Blockers:** None identified.
- **Progress:** Completed 2026-06-03. Full Aphrodite skill built at ~/.claude/skills/aphrodite/SKILL.md — direction and review modes with Anteros (brand) and Harmonia (layout) sub-agents. Standalone sub-skills also created.
- **Comments:** none
- **Modified:** 2026-06-05T16:02:56
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209676329024

### BSTD-006 — Resolve issue of local project sync with global studio sync
- **Local ID:** BSTD-006
- **Asana ID:** 1215209677652048
- **Section:** DONE
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** Mark Bain (507443625075), BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** needs separate commands
    get rid of pm-sync - and pm- prefix
    use studio- instead
- **Blockers:** None identified.
- **Progress:** Completed 2026-06-03. Renamed pm-asana-sync → studio-asana-sync, pm-retro → studio-retro, pm-todos → studio-todos, pm-onboard → studio-onboard via git mv in skills/. Updated symlinks and name: frontmatter fields. Fixed studio-pm agent reference /retro → /studio-retro. PR at https://github.com/markbain/bain-studio/pull/new/feature/bstd-006-rename-pm-skills-to-studio
- **Comments:** none
- **Modified:** 2026-06-05T16:02:55
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209677652048

### BSTD-016 — Create /studio-shutdown routine
- **Local ID:** BSTD-016
- **Asana ID:** 1215209677652054
- **Section:** DONE
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** Mark Bain (507443625075), BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** No notes.
- **Blockers:** None identified.
- **Progress:** Completed 2026-06-03. /studio-shutdown skill created — mirrors sync check, open branches audit, /studio-retro invocation, blocker report, Hermes notification. In bain-studio repo at skills/studio-shutdown/SKILL.md.
- **Comments:** none
- **Modified:** 2026-06-05T16:02:54
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209677652054

### BSTD-017 — Create /studio-startup routine
- **Local ID:** BSTD-017
- **Asana ID:** 1215209677652057
- **Section:** DONE
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** Mark Bain (507443625075), BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** No notes.
- **Blockers:** None identified.
- **Progress:** Completed 2026-06-03. /studio-startup skill created — syncs all mirrors, reads project pulse, invokes Abderus, checks financial snapshot, outputs morning report. In bain-studio repo at skills/studio-startup/SKILL.md.
- **Comments:** none
- **Modified:** 2026-06-05T16:02:53
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209677652057

### BSTD-018 — Create /studio-ghost-projects scans for inactive
- **Local ID:** BSTD-018
- **Asana ID:** 1215209407993905
- **Section:** DONE
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** Mark Bain (507443625075), BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** No notes.
- **Blockers:** None identified.
- **Progress:** Completed 2026-06-03. /studio-ghost-projects skill created — scans registered projects for stale mirrors (14d), inactive tasks (30d), orphaned branches, unanswered open questions. Reports active/stale/ghost/completed-unclosed with specific recommended actions. In bain-studio repo at skills/studio-ghost-projects/SKILL.md.
- **Comments:** none
- **Modified:** 2026-06-05T16:02:53
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209407993905

### BSTD-007 — Define delivery gate workflow
- **Local ID:** BSTD-007
- **Asana ID:** 1215209676891088
- **Section:** DONE
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** The Law of the Gate: Mark holds three gates no god may open alone. No delivery gate flow exists yet — define the Themis → Mark sign-off → Iris announce → Harvest trigger sequence.
- **Blockers:** None identified.
- **Progress:** Completed 2026-06-03. /studio-delivery-gate skill created — full 7-step sequence: Themis QA → gate package for Mark → approval gate → Iris announce → Poros invoice → Harvest → Asana closure. In bain-studio repo at skills/studio-delivery-gate/SKILL.md.
- **Comments:** none
- **Modified:** 2026-06-05T16:02:52
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209676891088

### BSTD-008 — Wire GNUCash collector into Plutus
- **Local ID:** BSTD-008
- **Asana ID:** 1215224928197756
- **Section:** DONE
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** gnucash_collector.py exists in collectors/. Confirm it is wired into Hermes cron and that Plutus can read its output for cashflow and tax projections.
- **Blockers:** None identified.
- **Progress:** Completed 2026-06-03. Verified: gnucash_collector.py writes to context/finance/accounts.json. Crontab runs it at 08:10 daily (10 8 * * * cd /media/data/dev/bain-studio && python3 studio/collectors/gnucash_collector.py). Plutus, Penia, and Euporia all read from accounts.json. No changes needed.
- **Comments:** none
- **Modified:** 2026-06-05T16:02:51
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215224928197756


## Changes This Sync

- NEW: BSTD-023 — Create the studio brand voice
- NEW: BSTD-019 — Fix VVV shutdown asking for password
## Immediate Priorities

| ID | Task | Status |
|----|------|--------|
| BSTD-022 | Conduct a security audit on the studio project | due 2026-06-05 |
| BSTD-023 | Create the studio brand voice | due 2026-06-08 |
| BSTD-005 | Replace ASANA_PAT with bainbot account token | no due date |
| BSTD-020 | Linked In job check - focus on new jobs | no due date |
| BSTD-010 | Audit and complete studio dashboard | no due date |
| BSTD-021 | Add API cost tracker to studio dashboard | no due date |
| BSTD-012 | Backfill Mnemosyne (project-database.csv) | no due date |