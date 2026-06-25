# Bot Asana Task Mirror
Last synced: 2026-06-25
Workspace GID: 512209774840
Assignee GID: 1209202434387214

## Bain Studio

### BSTD-041 — Join the WP theme review team
- **Local ID:** BSTD-041
- **Asana ID:** 1216010090994163
- **Section:** DONE
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** Mark Bain (507443625075), BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Join the theme review team. Use Claude to review the theme for issues. Is this already being done? Is there an official skill for theme review? Research this. Is there an email list? Slack channel?
- **Blockers:** None identified.
- **Progress:** Completed 2026-06-25. Research complete — docs/utilities/wp-theme-review.md. Not currently being done; no studio skill exists. Team communicates via WordPress.org Slack #themereview channel and themes@wordpress.org email. Meetings 2nd and 4th Tuesday at 15:00 UTC. Mark must join #themereview with his WordPress.org account; Claude can do the technical review work. Suggested workflow documented: pick ticket from Trac, run /wp-theme-review skill (to build), post review to Trac.
- **Comments:** none
- **Modified:** 2026-06-25T17:31:42
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1216010090994163

### BSTD-039 — Research Cloudways API — script application/server management
- **Local ID:** BSTD-039
- **Asana ID:** 1215964166735169
- **Section:** NEXT UP
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Goal: script everything so Claude can manage Cloudways servers (create apps, check disk, restart services, deploy) without manual platform login. Investigate Cloudways API coverage, auth, and what ops can be automated. Output: a report + any tooling added to studio.
- **Blockers:** None identified.
- **Progress:** Scope refined 2026-06-23. API research complete (docs/utilities/cloudways-api.md). Platform evaluation complete 2026-06-23: DO Premium 4GB ($54/mo) covers 3-6 WP projects; scales up/down via API; staging is linked clone with Pull-first convention for media; no shared media library but workflow is safe; Cloudways recommended over WP Engine for solo studio. Next: write ADR and provisioning guide.
- **Comments:** none
- **Modified:** 2026-06-25T17:31:43
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215964166735169

### BSTD-038 — Alert: Disk space is insufficient on server baindesign
- **Local ID:** BSTD-038
- **Asana ID:** 1215857733417784
- **Section:** NEXT UP
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** Mark Bain (507443625075), BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Mark Bain
--

BΛIП DΣƧIGП <https://bain.design>
𝕭𝖚𝖎𝖑𝖉 𝖜𝖎𝖙𝖍 ♥

---------- Forwarded message ---------
From: CloudwaysBot Notifications <success@cloudways.com <mailto:success@cloudways.com>>
Date: Fri, 19 Jun 2026 at 00:27
Subject: Alert: Disk space is insufficient on server baindesign
To:  <markbaindesign@gmail.com <mailto:markbaindesign@gmail.com>>

<https://email.cloudways.com/e/c/eyJlbWFpbF9pZCI6ImRnUzh5UUVCQUpxM0JacTNCUUdlM05rSE1jbGpHaEc4Y1VsaGF0WT0iLCJocmVmIjoiaHR0cDovL3d3dy5jbG91ZHdheXMuY29tL2VuLz91dG1fY2FtcGFpZ249Q2xvdWR3YXlzYm90K0Rpc2tIZWFsdGgrRXJyb3IrRGVmYXVsdFx1MDAyNnV0bV9jb250ZW50PUVtYWlsKzFcdTAwMjZ1dG1fbWVkaXVtPWVtYWlsX2FjdGlvblx1MDAyNnV0bV9zb3VyY2U9Y3VzdG9tZXIuaW8iLCJpbnRlcm5hbCI6ImJjYzkwMTAyYmFlMjAxOWFiNzA1IiwibGlua19pZCI6MTQ1MzUzMn0/cf537263a26d412da5d76d250ccf0ed5a1f64f3ede8def3c869832d0f3ad9045>

Hi there,

I, the CloudwaysBot, am here to inform you about an important event regarding your Cloudways server. The available disk space on your server baindesign is low. 95% or more of your disk has been occupied. This means (among other things) that no additional files and folders can be created and this will seriously hamper your application(s) functionality.

Application(s) can occupy unnecessary space due to logs, cache files, and sessions. In that case it is recommended to clear disk space from your application. You can check application disk space consumption via SSH <https://email.cloudways.com/e/c/eyJlbWFpbF9pZCI6ImRnUzh5UUVCQUpxM0JacTNCUUdlM05rSE1jbGpHaEc4Y1VsaGF0WT0iLCJocmVmIjoiaHR0cHM6Ly9zdXBwb3J0LmNsb3Vkd2F5cy5jb20vaG93LXRvLWNvbm5lY3QtdG8teW91ci1zZXJ2ZXItdXNpbmctc3NoLz91dG1fY2FtcGFpZ249Q2xvdWR3YXlzYm90K0Rpc2tIZWFsdGgrRXJyb3IrRGVmYXVsdFx1MDAyNnV0bV9jb250ZW50PUVtYWlsKzFcdTAwMjZ1dG1fbWVkaXVtPWVtYWlsX2FjdGlvblx1MDAyNnV0bV9zb3VyY2U9Y3VzdG9tZXIuaW8iLCJpbnRlcm5hbCI6ImJjYzkwMTAyYmFlMjAxOWFiNzA1IiwibGlua19pZCI6ODgwMjY3OH0/5e88fcb2014dc421e0f8982b622105aabdd10b6ba2d79c018ba42271c284a13e> or usage of disk via the Monitoring section in the Server Management area of the Cloudways Platform.

To resolve the situation, you can delete unnecessary files and folders to free up disk space or you can increase the server’s disk size <https://email.cloudways.com/e/c/eyJlbWFpbF9pZCI6ImRnUzh5UUVCQUpxM0JacTNCUUdlM05rSE1jbGpHaEc4Y1VsaGF0WT0iLCJocmVmIjoiaHR0cHM6Ly9zdXBwb3J0LmNsb3Vkd2F5cy5jb20vaG93LXRvLWluY3JlYXNlLWFwcGxpY2F0aW9uLWRpc2stc2l6ZS8_dXRtX2NhbXBhaWduPUNsb3Vkd2F5c2JvdCtEaXNrSGVhbHRoK0Vycm9yK0RlZmF1bHRcdTAwMjZ1dG1fY29udGVudD1FbWFpbCsxXHUwMDI2dXRtX21lZGl1bT1lbWFpbF9hY3Rpb25cdTAwMjZ1dG1fc291cmNlPWN1c3RvbWVyLmlvIiwiaW50ZXJuYWwiOiJiY2M5MDEwMmJhZTIwMTlhYjcwNSIsImxpbmtfaWQiOjQzMzIxNjU3fQ/d50cf140833f14c890050de30ee54605d2b3fd5c9cdf1f05ed49182d60d45880>.

Feel free to get in touch with the support team via Live Chat for questions/comments.

Thank you,

CloudwaysBot

www.cloudways.com <https://email.cloudways.com/e/c/eyJlbWFpbF9pZCI6ImRnUzh5UUVCQUpxM0JacTNCUUdlM05rSE1jbGpHaEc4Y1VsaGF0WT0iLCJocmVmIjoiaHR0cDovL3d3dy5DbG91ZHdheXMuY29tP3V0bV9jYW1wYWlnbj1DbG91ZHdheXNib3QrRGlza0hlYWx0aCtFcnJvcitEZWZhdWx0XHUwMDI2dXRtX2NvbnRlbnQ9RW1haWwrMVx1MDAyNnV0bV9tZWRpdW09ZW1haWxfYWN0aW9uXHUwMDI2dXRtX3NvdXJjZT1jdXN0b21lci5pbyIsImludGVybmFsIjoiYmNjOTAxMDJiYWUyMDE5YWI3MDUiLCJsaW5rX2lkIjoxMjc5ODU3fQ/02cc16669c251b710157b9d839115d2264f1ff185ad7a4c8bf7fe9d7e25adc6d>

Follow Us

<https://email.cloudways.com/e/c/eyJlbWFpbF9pZCI6ImRnUzh5UUVCQUpxM0JacTNCUUdlM05rSE1jbGpHaEc4Y1VsaGF0WT0iLCJocmVmIjoiaHR0cHM6Ly90d2l0dGVyLmNvbS9jbG91ZHdheXM_dXRtX2NhbXBhaWduPUNsb3Vkd2F5c2JvdCtEaXNrSGVhbHRoK0Vycm9yK0RlZmF1bHRcdTAwMjZ1dG1fY29udGVudD1FbWFpbCsxXHUwMDI2dXRtX21lZGl1bT1lbWFpbF9hY3Rpb25cdTAwMjZ1dG1fc291cmNlPWN1c3RvbWVyLmlvIiwiaW50ZXJuYWwiOiJiY2M5MDEwMmJhZTIwMTlhYjcwNSIsImxpbmtfaWQiOjIyMjA5NDh9/a8fff6844996797736549bf845a3426ebc5e97b2af4148784c40834619e3aac2>

<https://email.cloudways.com/e/c/eyJlbWFpbF9pZCI6ImRnUzh5UUVCQUpxM0JacTNCUUdlM05rSE1jbGpHaEc4Y1VsaGF0WT0iLCJocmVmIjoiaHR0cDovL3d3dy5mYWNlYm9vay5jb20vY2xvdWR3YXlzP3V0bV9jYW1wYWlnbj1DbG91ZHdheXNib3QrRGlza0hlYWx0aCtFcnJvcitEZWZhdWx0XHUwMDI2dXRtX2NvbnRlbnQ9RW1haWwrMVx1MDAyNnV0bV9tZWRpdW09ZW1haWxfYWN0aW9uXHUwMDI2dXRtX3NvdXJjZT1jdXN0b21lci5pbyIsImludGVybmFsIjoiYmNjOTAxMDJiYWUyMDE5YWI3MDUiLCJsaW5rX2lkIjoxMTE0Mjk5N30/3d520108ef3690e6165e2d4df033c0c08369eb3dc0b46623405812ebfe700945>

<https://email.cloudways.com/e/c/eyJlbWFpbF9pZCI6ImRnUzh5UUVCQUpxM0JacTNCUUdlM05rSE1jbGpHaEc4Y1VsaGF0WT0iLCJocmVmIjoiaHR0cDovL3d3dy5saW5rZWRpbi5jb20vY29tcGFueS9jbG91ZHdheXM_dXRtX2NhbXBhaWduPUNsb3Vkd2F5c2JvdCtEaXNrSGVhbHRoK0Vycm9yK0RlZmF1bHRcdTAwMjZ1dG1fY29udGVudD1FbWFpbCsxXHUwMDI2dXRtX21lZGl1bT1lbWFpbF9hY3Rpb25cdTAwMjZ1dG1fc291cmNlPWN1c3RvbWVyLmlvIiwiaW50ZXJuYWwiOiJiY2M5MDEwMmJhZTIwMTlhYjcwNSIsImxpbmtfaWQiOjQzMzAzMDc0fQ/8d7e112ca36ccdff93ba90d75b47364f4b302ee17296db9d99903fe5004a353b>

Join our Community <https://email.cloudways.com/e/c/eyJlbWFpbF9pZCI6ImRnUzh5UUVCQUpxM0JacTNCUUdlM05rSE1jbGpHaEc4Y1VsaGF0WT0iLCJocmVmIjoiaHR0cDovL2NvbW11bml0eS5jbG91ZHdheXMuY29tLz91dG1fY2FtcGFpZ249Q2xvdWR3YXlzYm90K0Rpc2tIZWFsdGgrRXJyb3IrRGVmYXVsdFx1MDAyNnV0bV9jb250ZW50PUVtYWlsKzFcdTAwMjZ1dG1fbWVkaXVtPWVtYWlsX2FjdGlvblx1MDAyNnV0bV9zb3VyY2U9Y3VzdG9tZXIuaW8iLCJpbnRlcm5hbCI6ImJjYzkwMTAyYmFlMjAxOWFiNzA1IiwibGlua19pZCI6NDMzMDMwNzV9/3cb207a494c34a8116cf7585504b4c02f5fc8f2c65b0d12c529f7e04a35747b0>

Read our Blog <https://email.cloudways.com/e/c/eyJlbWFpbF9pZCI6ImRnUzh5UUVCQUpxM0JacTNCUUdlM05rSE1jbGpHaEc4Y1VsaGF0WT0iLCJocmVmIjoiaHR0cDovL3d3dy5jbG91ZHdheXMuY29tL2Jsb2cvP3V0bV9jYW1wYWlnbj1DbG91ZHdheXNib3QrRGlza0hlYWx0aCtFcnJvcitEZWZhdWx0XHUwMDI2dXRtX2NvbnRlbnQ9RW1haWwrMVx1MDAyNnV0bV9tZWRpdW09ZW1haWxfYWN0aW9uXHUwMDI2dXRtX3NvdXJjZT1jdXN0b21lci5pbyIsImludGVybmFsIjoiYmNjOTAxMDJiYWUyMDE5YWI3MDUiLCJsaW5rX2lkIjo0MzMwMzA3Nn0/5bbfb134b079bd09ce2344e3f1cee585ee08a4c026073aa3a6eaf388ca9f10ba>

<https://email.cloudways.com/e/c/eyJlbWFpbF9pZCI6ImRnUzh5UUVCQUpxM0JacTNCUUdlM05rSE1jbGpHaEc4Y1VsaGF0WT0iLCJocmVmIjoiaHR0cDovL3d3dy5jbG91ZHdheXMuY29tL2VuLz91dG1fY2FtcGFpZ249Q2xvdWR3YXlzYm90K0Rpc2tIZWFsdGgrRXJyb3IrRGVmYXVsdFx1MDAyNnV0bV9jb250ZW50PUVtYWlsKzFcdTAwMjZ1dG1fbWVkaXVtPWVtYWlsX2FjdGlvblx1MDAyNnV0bV9zb3VyY2U9Y3VzdG9tZXIuaW8iLCJpbnRlcm5hbCI6ImJjYzkwMTAyYmFlMjAxOWFiNzA1IiwibGlua19pZCI6MTQ1MzUzMn0/cf537263a26d412da5d76d250ccf0ed5a1f64f3ede8def3c869832d0f3ad9045>

© 2026 Cloudways Ltd. All Rights Reserved.

52 Springvale, Pope Pius XII Street
Mosta MST2653, Malta.

-------

Want to stop receiving these emails from us?
Unsubscribe <https://email.cloudways.com/unsubscribe/dgS8yQEBAJq3BZq3BQGe3NkHMcljGhG8cUlhatY=>

Subject: Fwd: Alert: Disk space is insufficient on server baindesign
From: Bain Design <mark@bain.design>
To: "Asana (Bain Design)" <x@mail.asana.com>
Received: Fri, 19 Jun 2026 09:39:52 +0200
- **Blockers:** None identified.
- **Progress:** Checked 2026-06-25.
- **Comments:** none
- **Modified:** 2026-06-25T17:31:44
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215857733417784

### BSTD-032 — Research the best hosting platform for a client staging sites
- **Local ID:** BSTD-032
- **Asana ID:** 1215532073345538
- **Section:** NEXT UP
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** Mark Bain (507443625075), BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Going forward I want to build all client WordPress staging sites on a single hosting platform, one which I can automate/script and know inside out. Then I can break off "deploy to production" as a hourly rate project after I have been paid for the main project. Suggestions - Cloudways, WPE
    costs
    dev experience
    trade-offs
    pros, cons
- **Blockers:** None identified.
- **Progress:** Checked 2026-06-25.
- **Comments:** none
- **Modified:** 2026-06-25T17:31:46
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215532073345538

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
- **Modified:** 2026-06-25T17:31:47
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
- **Modified:** 2026-06-25T17:31:48
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
- **Modified:** 2026-06-25T17:31:48
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
- **Progress:** Checked 2026-06-25.
- **Comments:** none
- **Modified:** 2026-06-25T17:31:49
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215394379541907

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
- **Modified:** 2026-06-25T17:31:50
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
- **Progress:** Checked 2026-06-25.
- **Comments:**
  > 2026-06-05 **Mark Bain:** How can I grant this? Does this mean we can't do it?
- **Modified:** 2026-06-25T17:31:51
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
- **Modified:** 2026-06-25T17:31:51
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215209965255230

### BSTD-035 — Promote Mark to project admin / owner
- **Local ID:** BSTD-035
- **Asana ID:** 1215722386568076
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
- **Progress:** Checked 2026-06-25.
- **Comments:** none
- **Modified:** 2026-06-25T17:31:52
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215722386568076

### BSTD-025 — create a skill to open single project in terminal
- **Local ID:** BSTD-025
- **Asana ID:** 1215475893752388
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
- **Progress:** Done 2026-06-15. Created ~/bin/studio-open — Python script that reads studio/projects.json, looks up project path by ASANA_TASK_PREFIX in each CLAUDE.md, then calls ~/bin/open-project to open a new Terminator tab. Usage: `studio-open MCF` or `studio-open` to list. Wraps existing open-project which handles the 2-pane zsh+claude split.
- **Comments:** none
- **Modified:** 2026-06-25T17:31:53
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215475893752388

### BSTD-033 — create dev-ops.md
- **Local ID:** BSTD-033
- **Asana ID:** 1215706271185260
- **Section:** NEXT UP
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** Mark Bain (507443625075), BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** dev-ops.md is the source of truth doc for dev ops in every project. It forms part of the essential docs. It lists everything server and hosting related. Create a template with all the details I might need for dev ops. No passwords or keys!
- **Blockers:** None identified.
- **Progress:** Checked 2026-06-25.
- **Comments:** none
- **Modified:** 2026-06-25T17:31:54
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215706271185260

### BSTD-023 — Create the studio brand voice
- **Local ID:** BSTD-023
- **Asana ID:** 1215445632997592
- **Section:** NEXT UP
- **Due:** 2026-06-08 **(OVERDUE)**
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** Mark Bain (507443625075), BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** 1211312202132828 (1211312202132828), 1211859323827650 (1211859323827650), 1215445632997589 (1215445632997589), 1211859323827637 (1211859323827637)
- **Notes:** No notes.
- **Blockers:** 2026-06-23 — No notes or direction provided. Creating a brand voice requires Mark's input: intended tone (e.g. warm/direct/minimal), personality attributes, words/phrases to use and avoid, and examples of copy Mark considers on-brand. Cannot complete without this direction.
- **Progress:** Blocked 2026-06-23. Needs Mark to add notes with brand direction before this can be created. 4 dependent tasks are waiting on it.
- **Comments:** none
- **Modified:** 2026-06-25T17:31:54
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215445632997592

### BSTD-045 — Greenhouse: add #feature routing to obsidian_collector.py
- **Local ID:** BSTD-045
- **Asana ID:** 1216047224312667
- **Section:** TO DO
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Spec: context/internal/greenhouse-feature-pipeline.md (Phase 1). Add feature tag routing.
- **Blockers:** None identified.
- **Progress:** Designed 2026-06-25.
- **Comments:** none
- **Modified:** 2026-06-25T17:31:55
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1216047224312667

### BSTD-044 — Greenhouse: build /feature skill
- **Local ID:** BSTD-044
- **Asana ID:** 1216047425948674
- **Section:** TO DO
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Spec: context/internal/greenhouse-feature-pipeline.md (Phase 1). New skill at .claude/skills/feature/SKILL.md.
- **Blockers:** None identified.
- **Progress:** Designed 2026-06-25.
- **Comments:** none
- **Modified:** 2026-06-25T17:31:56
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1216047425948674

### BSTD-043 — Greenhouse: formalise greenhouse in /nurture + BSTD Asana
- **Local ID:** BSTD-043
- **Asana ID:** 1216047458985475
- **Section:** TO DO
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Spec: context/internal/greenhouse-feature-pipeline.md (Phase 2). Prereq: Mark must create Greenhouse section in BSTD Asana first.
- **Blockers:** 2026-06-25 — Mark must create a Greenhouse section in BSTD Asana UI before this task runs. Do not proceed until that section exists in the mirror.
- **Progress:** Designed 2026-06-25.
- **Comments:** none
- **Modified:** 2026-06-25T17:31:57
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1216047458985475

### BSTD-042 — Greenhouse: ADR 008 — three-tier idea pipeline
- **Local ID:** BSTD-042
- **Asana ID:** 1216047225478134
- **Section:** TO DO
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Spec: context/internal/greenhouse-feature-pipeline.md (Phase 3). Write docs/adr/008-three-tier-idea-pipeline.md and update studio-map.md.
- **Blockers:** None identified.
- **Progress:** Designed 2026-06-25.
- **Comments:** none
- **Modified:** 2026-06-25T17:31:58
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1216047225478134

### BSTD-031 — Complete subscription/DD account mapping (Aletheia Codex)
- **Local ID:** BSTD-031
- **Asana ID:** 1215560674534062
- **Section:** TO DO
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** No notes.
- **Blockers:** None identified.
- **Progress:** Checked 2026-06-25.
- **Comments:** none
- **Modified:** 2026-06-25T17:31:59
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215560674534062

### BSTD-030 — Backfill Q1 IVA Soportado entry (€141.11) — awaiting Mod 303 from gestor
- **Local ID:** BSTD-030
- **Asana ID:** 1215562863390244
- **Section:** TO DO
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** No notes.
- **Blockers:** None identified.
- **Progress:** Checked 2026-06-25.
- **Comments:** none
- **Modified:** 2026-06-25T17:31:59
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215562863390244

### BSTD-029 — Confirm Mod 130 / IRPF Retenido netting with gestor
- **Local ID:** BSTD-029
- **Asana ID:** 1215568533285470
- **Section:** TO DO
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** No notes.
- **Blockers:** None identified.
- **Progress:** Checked 2026-06-25.
- **Comments:** none
- **Modified:** 2026-06-25T17:32:00
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215568533285470


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
- **Progress:** Checked 2026-06-25.
- **Comments:** none
- **Modified:** 2026-06-25T17:32:20
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
- **Progress:** Checked 2026-06-25.
- **Comments:** none
- **Modified:** 2026-06-25T17:32:20
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
- **Progress:** Checked 2026-06-25.
- **Comments:** none
- **Modified:** 2026-06-25T17:32:19
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
- **Progress:** Checked 2026-06-25.
- **Comments:** none
- **Modified:** 2026-06-25T17:32:18
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
- **Modified:** 2026-06-25T17:32:17
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
- **Modified:** 2026-06-25T17:32:16
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
- **Modified:** 2026-06-25T17:32:15
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
- **Modified:** 2026-06-25T17:32:15
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
- **Modified:** 2026-06-25T17:32:14
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
- **Modified:** 2026-06-25T17:32:13
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
- **Modified:** 2026-06-25T17:32:12
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
- **Modified:** 2026-06-25T17:32:11
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
- **Modified:** 2026-06-25T17:32:10
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
- **Modified:** 2026-06-25T17:32:09
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215224928197756

### BSTD-028 — Fix Mod 130 estimate to deduct withheld IRPF
- **Local ID:** BSTD-028
- **Asana ID:** 1215533718530035
- **Section:** DONE
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** The upcoming expenses calculation in gnucash_parser.py estimates Mod 130 based on Q1 net income but does not deduct IRPF already withheld by Spanish clients (recorded in Assets:Future Assets:IRPF Retenido). This causes the estimate to be too high. Fix: sum IRPF Retenido transactions for the quarter and subtract from the Mod 130 estimate.
- **Blockers:** None identified.
- **Progress:** Done 2026-06-15. Added `_quarter_start()` helper and modified the Mod 130 branch in `_compute_upcoming()` to sum IRPF Retenido asset transactions (val > 0) from quarter start to today, subtract from the historical avg estimate, floor at 0. Adds `irpf_deducted` field to the upcoming entry when non-zero. gnucash_parser.py:283.
- **Comments:** none
- **Modified:** 2026-06-25T17:32:09
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215533718530035

### BSTD-022 — Conduct a security audit on the studio project
- **Local ID:** BSTD-022
- **Asana ID:** 1215386521408712
- **Section:** DONE
- **Due:** 2026-06-05 **(OVERDUE)**
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
- **Progress:** Done 2026-06-15. Full audit written to docs/utilities/security-audit-2026-06.md. Key findings: (1) HIGH — bainbot PAT hardcoded in settings.local.json allow rule, needs rotation by Mark; (2) MEDIUM — .env files were mode 664, fixed to 600; (3) MEDIUM — Bash(*) allow is unrestricted, accepted risk for solo dev; (4) MEDIUM — prompt injection possible from Asana/email content, added untrusted-content warning to CLAUDE.md. Contagion: Edit/Write cross-project is blocked by hook; reads are not. VM: not needed for current workflow.
- **Comments:** none
- **Modified:** 2026-06-25T17:32:08
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215386521408712

### BSTD-026 — create studio wordpress plugin knowledge base
- **Local ID:** BSTD-026
- **Asana ID:** 1215490034697255
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
- **Progress:** Done 2026-06-15. Created docs/gods/hephaestus/wordpress-plugins.md — 178-line KB covering 16 plugins (Divi, Elementor, WPML, WooCommerce, MemberPress, LearnDash, Yoast, Algolia, Gravity Forms, WPGraphQL, WP All Import, ACF, WP Migrate DB, cookie consent, WP Offload Media) with use cases, key hooks/filters, gotchas, and studio patterns per plugin.
- **Comments:** none
- **Modified:** 2026-06-25T17:32:07
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215490034697255

### BSTD-027 — create a studio skill / script cheatsheet
- **Local ID:** BSTD-027
- **Asana ID:** 1215490034697251
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
- **Progress:** Done 2026-06-15. Created docs/cheatsheet.md — 168-line quick reference covering all skills (grouped by category), ~/bin/ scripts, studio Python scripts, and key files. Frontmatter tagged for Obsidian index.
- **Comments:** none
- **Modified:** 2026-06-25T17:32:06
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215490034697251

### BSTD-036 — Get a free Google Cloud API key for PageSpeed Insights
- **Local ID:** BSTD-036
- **Asana ID:** 1215806122078819
- **Section:** DONE
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Create free API keys for (1) PageSpeed Insights API and (2) Google Search Console API — both in the same Google Cloud project, no billing required.

Steps:
1. Go to console.cloud.google.com
2. Create or select a project
3. Enable PageSpeed Insights API
4. Enable Google Search Console API
5. Credentials → Create API Key (one key covers both)
6. Store in studio .env or pass as --api-key when running seo_audit.py

Why PSI: fixes 429 rate limiting on seo-audit. Needed to get CWV/performance scores for NORE (blocked 2026-06-17).

Why GSC API: enables Aura to pull keyword rankings, impressions, CTR per page, and URL indexing status programmatically. GSC is already set up on NORE. No equivalent free alternative exists.

Cross-ref: NORE-023.
- **Blockers:** None identified.
- **Progress:** Completed 2026-06-18. API key created, stored in studio/.env, tested against bain.design — PSI returning CWV data.
- **Comments:** none
- **Modified:** 2026-06-25T17:32:05
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215806122078819

### BSTD-037 — Research Hermes agent
- **Local ID:** BSTD-037
- **Asana ID:** 1215810739951650
- **Section:** DONE
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** Mark Bain (507443625075), BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** https://hermes-agent.nousresearch.com/
- **Blockers:** None identified.
- **Progress:** Completed 2026-06-23. Nous Research's Hermes Agent is an open-source multi-platform AI agent (MIT). Not relevant to current studio tooling - low overlap with Claude Code workflow. Research note at docs/utilities/nous-hermes-agent.md. Recommendation: no action, monitor Nous model releases.
- **Comments:** none
- **Modified:** 2026-06-25T17:32:03
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215810739951650

### BSTD-024 — Use ai to contribute to Wordpress
- **Local ID:** BSTD-024
- **Asana ID:** 1215445592095018
- **Section:** DONE
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** project-seed   (1215722387910965)
- **Followers:** Mark Bain (507443625075), BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** this is a project seed
    wp-contributor project
    check if there is an api or rss feed of issues, esp good issues for first contribution
    set up a factory to contribute 
    research the process of contribution - create a report and a project spec.md
- **Blockers:** None identified.
- **Progress:** Completed 2026-06-23. Gutenberg GitHub PRs identified as best entry point — Good First Issue label, fully queryable via API, standard PR flow. Research at docs/utilities/wp-contributor.md. Project spec at specs/drafts/wp-contributor-spec.md. Next step: build fetch-issues.py script and fork WordPress/gutenberg under Mark's account.
- **Comments:**
  > 2026-06-15 **Mark Bain:** I have contributed to Shutter!!! So, you know...
- **Modified:** 2026-06-25T17:32:02
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1215445592095018

### BSTD-040 — ID third party plugins looking for contributors
- **Local ID:** BSTD-040
- **Asana ID:** 1216010090994159
- **Section:** DONE
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** none
- **Followers:** Mark Bain (507443625075), BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Plugins in the WP repo sometimes are calling for contributors or PRs for changes or enhancements. Find some to work on alongside core contribution.
- **Blockers:** None identified.
- **Progress:** Completed 2026-06-25. Researched GitHub for third-party WP plugins with active contributor programmes. Top targets: WooCommerce (52 good-first-issues), Yoast SEO (12), WP Playground (12), Action Scheduler (4). Report saved to docs/utilities/wp-third-party-contributors.md.
- **Comments:** none
- **Modified:** 2026-06-25T17:32:01
- **URL:** https://app.asana.com/1/512209774840/project/1215208851588912/task/1216010090994159

### BSTD-034 — Create CRM
- **Local ID:** BSTD-034
- **Asana ID:** 1215722387910960
- **Section:** NEXT UP
- **Due:** none
- **Start:** none
- **Assignee:** BainBot (1209202434387214)
- **Assignee Status:** inbox
- **Tags:** project-seed   (1215722387910965)
- **Followers:** Mark Bain (507443625075), BainBot (1209202434387214)
- **Dependencies:** none
- **Dependents:** none
- **Notes:** Build or install a CRM for tracking prospects and existing clients over the long term. Check if there is a free open source alternative or build our own. Needs API to pull into studio dashboard. Based around .md with frontmatter. Obsidian layer? Decide what goes in - freelance clients? Upwork jobs? Potential employers? Separate systems or one? Planning + sign off before execution. Research it.
- **Blockers:** None identified.
- **Progress:** Checked 2026-06-25.
- **Comments:** none
- **Modified:** 2026-06-25T17:31:45
- **URL:** https://app.asana.com/1/512209774840/project/1206307486602881/task/1215722387910960

## Immediate Priorities

| ID | Task | Status |
|----|------|--------|
| BSTD-023 | Create the studio brand voice | 2026-06-08 OVERDUE |
| BSTD-041 | Join the WP theme review team | no due date |
| BSTD-039 | Research Cloudways API — script application/server | no due date |
| BSTD-038 | Alert: Disk space is insufficient on server bainde | no due date |
| BSTD-032 | Research the best hosting platform for a client st | no due date |
| BSTD-005 | Replace ASANA_PAT with bainbot account token | no due date |