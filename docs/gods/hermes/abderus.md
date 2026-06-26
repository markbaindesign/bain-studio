---
description: Timing sweep — surfaces harvest gaps, overdue tasks, stale leads, and
  pending follow-ups
god: hermes
invoke: /abderus
role: Scheduler
tags:
- skill
- agent
---

# Abderus — Timing Sweep

Checks every time-sensitive obligation in the studio and surfaces what needs action today. Named after Hermes's scheduler — he is the one who notices what is slipping.

## Invoke

```
/abderus
```

Usually called automatically by `/studio-startup`, but can be run standalone for a pulse check.

## Sources checked

| Source | What it checks |
|---|---|
| `project-database.csv` | End Date, harvest status per project |
| `{CONTENT_DIR}/pipeline/triage-log.md` | Investigate verdicts with no follow-up |
| Active project Asana mirrors | `.claude/asana-mirror.md` per project |

## Checks run

### 1. Harvest gaps
For every project with an End Date:
- Flags if any of Case Study, Blog Post, or Testimonial Status is `none` or `draft` AND End Date was more than 14 days ago
- Escalates if more than 60 days have elapsed

### 2. Testimonial follow-ups
Flags projects where Testimonial Status is `requested` and more than 21 days have passed since End Date — prompts a follow-up nudge.

### 3. Stale triage entries
Finds any entry in the triage log with verdict `Investigate` that has no follow-up recorded.

### 4. Overdue Asana tasks
Scans active project mirrors for tasks past their due date with no completion.

## Output format

```
== Abderus Timing Sweep — {date} ==

HARVEST GAPS
  {Project}  (ended {N} days ago)  Missing: blog post, testimonial

TESTIMONIAL FOLLOW-UPS
  {Project}  (requested {N} days ago)  — due a nudge

STALE TRIAGE
  {slug}  Investigate verdict, no follow-up recorded

OVERDUE TASKS
  [{PREFIX}] {Task name}  (due {date}, {N} days ago)
```

## Notes

- Abderus does not act — he reports. Acting on his findings is Mark's job.
- The 14-day harvest grace period exists because the first two weeks post-delivery are usually still in the client's lap.
- Law V applies: every completed project yields a blog post, a case study, and a testimonial request. Abderus enforces this by surfacing gaps until they are resolved.

## See also

- [harvest.md](harvest.md) — the skill that produces the missing artefacts Abderus flags
- [triage.md](triage.md) — where triage log entries come from
