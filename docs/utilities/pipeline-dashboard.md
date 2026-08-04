---
tags: [tool, service]
command: "systemctl --user start pipeline-dashboard"
description: Upwork pipeline Flask dashboard — persistent systemd user service on port 5050
---

# pipeline-dashboard

Flask web dashboard for the Upwork proposal pipeline. Runs as a persistent systemd user service (starts on login, restarts on failure).

## Service management

```bash
systemctl --user status pipeline-dashboard    # check
systemctl --user restart pipeline-dashboard   # restart
systemctl --user stop pipeline-dashboard      # stop
journalctl --user -u pipeline-dashboard -f    # live logs
```

## URLs

- Dashboard UI: http://localhost:5050
- API status: http://localhost:5050/api/status
- Pending briefs: http://localhost:5050/api/briefs

## API endpoints

| Method | Path | What it returns |
|---|---|---|
| GET | `/api/status` | Pipeline stats — seen, passed, applied, connects burn |
| GET | `/api/briefs` | Pending briefs awaiting Mark's reply |
| POST | `/apply/<thread_id>` | Mark a brief as applied |
| POST | `/reject/<thread_id>` | Mark a brief as rejected |
| POST | `/outcome/<thread_id>` | Record win/loss outcome |
| POST | `/interview/<thread_id>` | Flag as interview stage |
| POST | `/connects/<thread_id>` | Update connects count for a job |
| GET | `/settings` | Read scoring thresholds |
| POST | `/settings` | Update scoring thresholds |

## Service file

`~/.config/systemd/user/pipeline-dashboard.service`

```ini
[Unit]
Description=Upwork Pipeline Dashboard
After=network.target

[Service]
WorkingDirectory=/media/data/dev/misc/upwork-proposals
ExecStart=/media/data/dev/misc/upwork-proposals/.venv/bin/python pipeline/dashboard.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

## Notes

- Source: `pipeline/dashboard.py` in the upwork-proposals repo
- State is read from `pipeline/pending_briefs.json` — not Asana
- Application status (applied/rejected) is tracked via Gmail labels, not this service
- The studio dashboard (`bain-studio/studio/dashboard/`) proxies `/api/status` via `server.py`
