# Bot Asana Task Mirror
<!--
MIRROR FORMAT — each task block looks like this:

### {PREFIX}-{NNN} — {Task name}
- **Local ID:** {PREFIX}-{NNN}
- **Asana ID:** {asana_task_gid}
- **Section:** {DOING|NEXT UP|TO DO|DONE|SOMEDAY/MAYBE}
- **Due:** {YYYY-MM-DD or none}
- **Start:** {YYYY-MM-DD or none}
- **Assignee:** {Name} ({gid})
- **Assignee Status:** {inbox|today|upcoming|later}
- **Tags:** {tag name (gid), ... or none}
- **Followers:** {Name (gid), ...}
- **Dependencies:** {PREFIX-NNN, ... or none}
- **Dependents:** {PREFIX-NNN, ... or none}
- **Notes:** {task description — edit freely, syncs to Asana}
- **Blockers:** {freeform blocker text — edit freely, does NOT sync}
- **Progress:** {freeform progress note — syncs to Asana as a comment if changed}
- **Modified:** {ISO timestamp — set by Asana, used for conflict resolution}
- **URL:** https://app.asana.com/1/{workspace_gid}/project/{project_gid}/task/{task_gid}

EDITING RULES:
- Edit Notes, Section, Due, Start, Tags, Followers, Dependencies, Dependents, Assignee Status, Progress freely
- Blockers is local-only — never pushed to Asana
- Progress syncs as a comment only when changed
- Do NOT edit Local ID, Asana ID, Modified, or URL — these are managed by sync.py
- sync.py wins if Asana was modified more recently than the last sync
-->

Last synced: 2026-05-28
Workspace GID: 512209774840
Assignee GID: 1209202434387214

## Bain Studio

### BSTD-001 — Flesh out Iris skill
- **Local ID:** BSTD-001
- **Asana ID:** 1215209677218047
- **Section:** NEXT UP
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
- **Progress:** Checked 2026-05-28.
- **Modified:** 2026-05-28T16:32:44
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209677218047

### BSTD-002 — Flesh out Themis skill
- **Local ID:** BSTD-002
- **Asana ID:** 1215209811194641
- **Section:** NEXT UP
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
- **Progress:** Checked 2026-05-28.
- **Modified:** 2026-05-28T16:32:41
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209811194641

### BSTD-003 — Flesh out Hephaestus skill
- **Local ID:** BSTD-003
- **Asana ID:** 1215209663836183
- **Section:** NEXT UP
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
- **Progress:** Checked 2026-05-28.
- **Modified:** 2026-05-28T16:32:39
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209663836183

### BSTD-004 — Flesh out Aphrodite skill
- **Local ID:** BSTD-004
- **Asana ID:** 1215209676329024
- **Section:** NEXT UP
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
- **Progress:** Checked 2026-05-28.
- **Modified:** 2026-05-28T16:32:37
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209676329024

### BSTD-005 — Replace ASANA_PAT with bainbot account token
- **Local ID:** BSTD-005
- **Asana ID:** 1215209467864880
- **Section:** NEXT UP
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Generate from Asana as bainbot user at app.asana.com → My Settings → Apps → Personal Access Tokens
- **Blockers:** None identified.
- **Progress:** Checked 2026-05-28.
- **Modified:** 2026-05-28T16:24:03
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209467864880

### BSTD-006 — Resolve issue of local project sync with global studio sync
- **Local ID:** BSTD-006
- **Asana ID:** 1215209677652048
- **Section:** NEXT UP
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
- **Progress:** Checked 2026-05-28.
- **Modified:** 2026-05-28T16:29:05
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209677652048

### BSTD-007 — Define delivery gate workflow
- **Local ID:** BSTD-007
- **Asana ID:** 1215209676891088
- **Section:** TO DO
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
- **Progress:** Checked 2026-05-28.
- **Modified:** 2026-05-28T16:32:55
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209676891088

### BSTD-008 — Wire GNUCash collector into Plutus
- **Local ID:** BSTD-008
- **Asana ID:** 1215224928197756
- **Section:** TO DO
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
- **Progress:** Checked 2026-05-28.
- **Modified:** 2026-05-28T16:32:53
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215224928197756

### BSTD-009 — Automate case study → website delivery pipeline
- **Local ID:** BSTD-009
- **Asana ID:** 1215209965255230
- **Section:** TO DO
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Portfolio folder and workshop templates built. Wire up: workshop.md → generate upwork.md + website.md → screenshot assets → deliver to bain.design content/inbox. Screenshot script still needed (task #1 in session).
- **Blockers:** None identified.
- **Progress:** Checked 2026-05-28.
- **Modified:** 2026-05-28T16:32:51
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209965255230

### BSTD-010 — Audit and complete studio dashboard
- **Local ID:** BSTD-010
- **Asana ID:** 1215209663490357
- **Section:** TO DO
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
- **Progress:** Checked 2026-05-28.
- **Modified:** 2026-05-28T16:32:49
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209663490357

### BSTD-011 — Build The Notifier
- **Local ID:** BSTD-011
- **Asana ID:** 1215209965001262
- **Section:** TO DO
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
- **Progress:** Checked 2026-05-28.
- **Modified:** 2026-05-28T16:32:47
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209965001262

### BSTD-012 — Backfill Mnemosyne (project-database.csv)
- **Local ID:** BSTD-012
- **Asana ID:** 1215209677034138
- **Section:** TO DO
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** The studio project ledger is empty or sparse. Backfill completed projects using the log-project skill — client, sector, stack, estimate vs actuals, outcome grade, lessons. Mnemosyne grows wiser with every project entered.
- **Blockers:** None identified.
- **Progress:** Checked 2026-05-28.
- **Modified:** 2026-05-28T16:32:46
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209677034138

### BSTD-013 — Set custom project icon on new Asana projects
- **Local ID:** BSTD-013
- **Asana ID:** 1215209467867245
- **Section:** TO DO
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
- **Progress:** Checked 2026-05-28.
- **Modified:** 2026-05-28T16:24:09
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209467867245

### BSTD-014 — Set up Telegram notifications for rate limit reset
- **Local ID:** BSTD-014
- **Asana ID:** 1215209394424148
- **Section:** TO DO
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
- **Progress:** Checked 2026-05-28.
- **Modified:** 2026-05-28T16:24:06
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209394424148


## Changes This Sync

- NEW: BSTD-007 — Define delivery gate workflow
- NEW: BSTD-013 — Set custom project icon on new Asana projects
- NEW: BSTD-010 — Audit and complete studio dashboard
- NEW: BSTD-004 — Flesh out Aphrodite skill
- NEW: BSTD-014 — Set up Telegram notifications for rate limit reset
- NEW: BSTD-003 — Flesh out Hephaestus skill
- NEW: BSTD-001 — Flesh out Iris skill
- NEW: BSTD-005 — Replace ASANA_PAT with bainbot account token
- NEW: BSTD-011 — Build The Notifier
- NEW: BSTD-006 — Resolve issue of local project sync with global studio sync
- NEW: BSTD-008 — Wire GNUCash collector into Plutus
- NEW: BSTD-012 — Backfill Mnemosyne (project-database.csv)
- NEW: BSTD-002 — Flesh out Themis skill
- NEW: BSTD-009 — Automate case study → website delivery pipeline
## Immediate Priorities

| ID | Task | Status |
|----|------|--------|
| BSTD-001 | Flesh out Iris skill | no due date |
| BSTD-002 | Flesh out Themis skill | no due date |
| BSTD-003 | Flesh out Hephaestus skill | no due date |
| BSTD-004 | Flesh out Aphrodite skill | no due date |
| BSTD-005 | Replace ASANA_PAT with bainbot account token | no due date |