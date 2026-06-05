---
name: abderus
description: Run the studio timing sweep — surfaces harvest gaps, stale projects, pending follow-ups, and overdue obligations. Run at the start of a work session or when you want a pulse check on what's slipping. Abderus is Hermes's scheduler.
---

# Abderus — Timing Sweep

Check every time-sensitive obligation in the studio and surface what needs action today.

## Sources to read

Read all of the following that exist:

1. `/media/data/dev/misc/upwork-proposals/context/portfolio/project-database.csv` — End Date, harvest status fields (Case Study, Blog Post, Testimonial Status)
2. `{CONTENT_DIR}/pipeline/triage-log.md` — inbound signals logged as "Investigate" with no follow-up recorded
3. Active project Asana mirrors — `.claude/asana-mirror.md` in each active project directory (paths from CLAUDE.md active projects table)

Today's date is available from context. Use it to calculate days elapsed.

## Checks to run

### 1. Harvest gaps

For every row in project-database.csv where End Date is set:
- Calculate days since End Date
- Flag if any of Case Study, Blog Post, or Testimonial Status is `none` or `draft` AND End Date was more than 14 days ago
- Flag more urgently if End Date was more than 60 days ago

Output per project: name, end date, days elapsed, which harvest items are missing.

### 2. Testimonial follow-ups

For every row where Testimonial Status is `requested`:
- Check if End Date was more than 21 days ago — if so, flag for a follow-up nudge
- Note: do not flag if status is `received` or `published`

### 3. Stale triage entries

In `{CONTENT_DIR}/pipeline/triage-log.md`, find any entry with:
- Verdict: `Investigate`
- No follow-up action logged (no subsequent entry for the same client)
- Date more than 5 days ago

Flag these — an unanswered investigation is a lost lead or an ignored problem.

### 4. Active project health

For each active project in CLAUDE.md, check its Asana mirror:
- When was the mirror last synced? (check the timestamp at the top of asana-mirror.md)
- Are there overdue tasks? (due date in the past, status not complete)

Flag projects with mirrors older than 3 days or overdue tasks.

## Output format

Produce a concise sweep report. Omit any section that has nothing to flag — no padding.

```
## Abderus Sweep — YYYY-MM-DD

### Harvest gaps
- **[Project Name]** — closed [N] days ago. Missing: [case study / blog post / testimonial request].
  → Run /harvest [project name]

### Testimonial follow-ups
- **[Project Name]** — testimonial requested [N] days ago, no response yet.
  → Send a gentle nudge.

### Stale triage
- **[Client name] ([date])** — marked Investigate, no follow-up in [N] days.
  → Check {CONTENT_DIR}/pipeline/triage-log.md and decide: pursue, decline, or close.

### Project health
- **[Project]** — Asana mirror [N] days old. [X] overdue tasks.
  → Run /pm-asana-sync in that project.

### All clear
[List any domain that had nothing to flag, for completeness.]
```

## Notes

- If project-database.csv has no rows yet, note it and suggest running `/log-project` to backfill past projects.
- If triage-log.md does not exist, skip that check silently.
- Do not flag projects where Would Repeat = FALSE for testimonial follow-ups — don't chase testimonials from clients you wouldn't work with again.
- Abderus reports facts. He does not make decisions. Routing and response drafting belongs to the invoked skill (/harvest, /triage, /pm-asana-sync).
