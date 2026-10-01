---
tags: [tool, dashboard, ops]
god: hermes
command: studio/scripts/dashboard-app.sh
description: Studio dashboard on port 5555 - Highlights home, finance, KF time budget, Upwork pipeline and Ops tabs. Not the Upwork pipeline dashboard on 5050.
---

# Studio dashboard

Flask server plus a single-page frontend in `studio/dashboard/`. See ADR 004. Not to be confused
with the Upwork [[pipeline-dashboard]], which is a separate service on port 5050 (this one proxies
its API for the Pipeline tab).

```bash
studio/scripts/dashboard-app.sh        # starts the server if needed, opens a standalone Chromium app window
python3 studio/dashboard/server.py     # server only, http://localhost:5555
```

`dashboard-app.sh` is also installed as a "Studio Dashboard" desktop entry
(`~/.local/share/applications/studio-dashboard.desktop`).

## Tabs

| Tab | Source |
|---|---|
| **Highlights** (home) | Aggregates the other tabs into a ranked "act / watch / info" list, plus Claude usage |
| Financial | GnuCash + Harvest, `/api/data` |
| KF Time Budget | `harvest_kf_collector` snapshot, `/api/kf` |
| Pipeline | Upwork pipeline API on 5050 |
| Ops | Crontab entries against their log files, `/api/ops` |

### Highlights

Flags missed scheduled jobs, BBVA shortfall, overdue invoices, payments due within 7 days,
uninvoiced time, KF pace, high-score briefs awaiting a decision, and Claude quota pace.

**Claude usage** reads `~/.claude/ratelimit-current.json`, which `~/.claude/hooks/statusline.py`
rewrites on every status line refresh (scoped to the active `CLAUDE_CONFIG_DIR`). Figures go stale
when no Claude session is open. Pace checks:

- **Weekly:** 5 work days at 20% each (Mon-Fri), weekends budget nothing; the window opens 7 days
  before the reset time.
- **5-hour:** straight-line, 20% per hour from when the window opened.

Over by more than 5 points is amber, more than 15 is red.

### Ops

`studio/dashboard/ops_status.py` reads `crontab -l`, works out when each job last should have
fired, and compares that with its log file's modification time. Job names link to
`/ops/log/<name>` (last 500 lines as plain text, `?lines=0` for all). Only logs named in the
crontab are served, looked up by job name, never by path.

Limits: a job that runs but writes nothing shows as missed, and jobs that log outside any
crontab-visible file show "no log". Cron does not catch up on runs missed while the machine was
off, so a late boot shows up here as a block of missed 08:xx jobs.
