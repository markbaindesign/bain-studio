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
| Finance | GnuCash accounts in real use not updated for 14+ days; BBVA shortfall and negative liquid cash (from `accounts.json`); every closed month recently below break-even; next quarterly filing within 45 days unless logged as filed in `aletheia-codex.md`; money tasks (invoice, budget, tax, renewal...) that are **overdue**. A task merely due soon is not a finding: it is on schedule, and Asana already shows it |
| Operations | Every crontab job with a `>>` log: failing (error in the last lines of its log) or quiet (log not written within its schedule; `high` once silent for 3 of its own cycles, `QUIET_CYCLES_HIGH`); `accounts.json` stale; uncommitted changes older than a week in registered repos; feature/release/hotfix branches unmerged for 2+ weeks |
| Projects | Overdue tasks; looper tasks Blocked on Mark; tasks in Review for 7+ days; open tasks untouched for 60+ days (`UNTOUCHED_AFTER_DAYS`, rolled up past 5 per project); active projects with no task activity for 30 days. A project with more than 5 overdue tasks gets one summary finding instead of flooding Today |
| Clients | Chase / sign-off / client-action / follow-up tasks with no movement for 14+ days |

Paused and archived projects are skipped. SL/SLT are skipped: their tasks appear in home mirrors.

## Ranking and escalation

Severity means:

| Level | Meaning |
|---|---|
| `critical` | money or statutory consequence, irreversible if ignored. **Only a check sets this**, never ageing |
| `high` | real work dropped and costing something: a client waiting, a job dead for weeks |
| `normal` | should be picked up, no consequence yet |

**Severity belongs to the problem, not to the report.** Each check derives it from the age of the
thing itself: how many days a task is overdue, how long a job has been silent, how far behind the
books are. Nothing is promoted for having been on the list a while.

That used to be otherwise, and it was the single biggest fault in the brief. A finding unresolved
for 7 days was bumped a level every run, so on 2026-09-30 the brief carried 58 criticals of which
**57 had been put there by the clock** rather than by a check. Because the state file had been
seeded on one day, they all escalated together and the same eight items sat in Today indefinitely.
Re-running the same data after the fix: 1 critical.

`studio/collectors/daily_brief_state.json` (gitignored) still records when each finding was first
raised, but only to print "raised N days ago" and to break ties in ranking. Resolved findings drop
out of the state.

**Today** lists up to 8 critical/high findings, ranked by severity, then **acute before chronic**,
then by the age of the problem, then by how long it has been reported. Each area follows with every
finding, grouped by project.

An *acute* finding is something erroring right now rather than rotting slowly: a cron job whose last
run failed, a transcription failing repeatedly, a crashed check, an unreadable GnuCash book or
finance snapshot. Age alone cannot express this, because a job that broke on its last run has an age
of zero and would sort below a task 476 days overdue. Pass `acute=True` to `finding()` when adding a
check that detects live breakage.

## Tuning

Thresholds are constants at the top of the script (`OVERDUE_ROLLUP`, `UNTOUCHED_AFTER_DAYS`,
`UNTOUCHED_HIGH_DAYS`, `UNTOUCHED_ROLLUP`, `PROJECT_STALE_HIGH_DAYS`, `QUIET_CYCLES_HIGH`,
`VOICE_NOTE_STALE_DAYS`,
`BOOKS_STALE_DAYS`, `BUSY_ACCOUNT_ENTRIES`, `DORMANT_AFTER_DAYS`). Adding a check means giving it
an age-based severity rule of its own, since nothing else will raise it later. Jobs that log somewhere other than
their cron `>>` file go in `QUIET_JOB_LOGS`. Output folder: `DAILY_BRIEF_DIR`, else
`$OBSIDIAN_VAULT/Daily Brief`.

## What it deliberately does not report

The brief is a **safety net for work that has been missed**, not a task list. Mark manages tasks in
Asana. A finding has to pass both halves of one test: *has this actually been missed, and would
anything else put it in front of him?* A task that is merely due today or due soon fails both, so
there is no "due soon" check. The two forward-looking exceptions, the cashflow shortfall forecast
and statutory filing dates, are kept on the second ground rather than the first: nothing else is
watching them.

## Related

- [abderus.md](abderus.md) — the interactive timing sweep skill this automates
- [postman.md](postman.md), `studio/notifier.py` — Slack delivery
