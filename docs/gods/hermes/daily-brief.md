---
tags: [tool, collector, chief-of-staff]
god: hermes
command: python3 studio/collectors/daily_brief.py
description: Daily chief-of-staff sweep - finds what's slipping across finance, operations, projects and clients, writes a ranked note to Work Notes and pings Slack
---

# Daily Brief

Abderus's morning report. A deterministic script (no Claude call) that sweeps the studio for things
being dropped, ranks them, writes `Work Notes/Daily Brief/YYYY-MM-DD-daily-brief.md` and posts
the top items to Slack with a link that opens the note in Obsidian.

Built 2026-09-17 because warnings already existed but went unread: the GnuCash collector had
been logging a BBVA shortfall every morning, and the KF Harvest collector had failed daily since
July, with nothing bringing either to Mark.

## Run

```bash
python3 studio/collectors/daily_brief.py              # write note, update state, notify Slack
python3 studio/collectors/daily_brief.py --dry-run    # print the note only
python3 studio/collectors/daily_brief.py --no-notify  # write the note, skip Slack
```

Cron (ops worktree, after sync, Hermes and the GnuCash collector):

```
40 8 * * * cd /home/bain/ops/bain-studio && python3 studio/collectors/daily_brief.py >> studio/collectors/daily_brief.log 2>&1
```

## What it checks

| Area | Checks |
|---|---|
| Finance | GnuCash accounts in real use not updated for 14+ days; BBVA shortfall and negative liquid cash (from `accounts.json`); every closed month recently below break-even; next quarterly filing within 45 days unless logged as filed in `aletheia-codex.md`; money tasks (invoice, budget, tax, renewal...) overdue or due within 14 days |
| Operations | Every crontab job with a `>>` log: failing (error in the last lines of its log) or quiet (log not written within its schedule); `accounts.json` stale; uncommitted changes older than a week in registered repos; feature/release/hotfix branches unmerged for 2+ weeks |
| Projects | Overdue tasks; looper tasks Blocked on Mark; tasks in Review for 7+ days; active projects with no task activity for 30 days. A project with more than 5 overdue tasks gets one summary finding instead of flooding Today |
| Clients | Chase / sign-off / client-action / follow-up tasks with no movement for 14+ days |

Paused and archived projects are skipped. SL/SLT are skipped: their tasks appear in home mirrors.

## Ranking and escalation

Severity is `normal`, `high` or `critical`. `studio/collectors/daily_brief_state.json` (gitignored)
records when each finding was first raised. After 7 days a still-open finding goes up one level
and the note marks it escalated, the way a CFO asks again rather than repeating the same email.
Resolved findings drop out of the state. **Today** lists up to 8 critical/high findings, most
severe and longest-ignored first; each area follows with every finding, grouped by project.

## Tuning

Thresholds are constants at the top of the script (`ESCALATE_AFTER_DAYS`, `OVERDUE_ROLLUP`,
`BOOKS_STALE_DAYS`, `BUSY_ACCOUNT_ENTRIES`, `DORMANT_AFTER_DAYS`). Jobs that log somewhere other than
their cron `>>` file go in `QUIET_JOB_LOGS`. Output folder: `DAILY_BRIEF_DIR`, else
`$OBSIDIAN_VAULT/Daily Brief`.

## Related

- [abderus.md](abderus.md) — the interactive timing sweep skill this automates
- [postman.md](postman.md), `studio/notifier.py` — Slack delivery
