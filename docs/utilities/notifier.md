---
command: python3 studio/notifier.py
description: Sends Slack notifications from any agent — urgent, high, normal, or low
  priority
tags:
- tool
---

# notifier.py — Slack Notifications

Sends formatted alerts to Slack. Used directly by agents and internally by `postman.py` for high/urgent messages.

## Volume control

Only `high` and `urgent` reach Slack. `low` and `normal` are dropped (the call returns
`False`), because the same news is already in Asana or the logs and Slack had become noise.
Set `SLACK_MIN_PRIORITY` in `studio/.env` (`low`, `normal`, `high`, `urgent`) to move the
floor.

## Python API

```python
from studio.notifier import notify

notify("Deploy complete on ACME", priority="normal", sender="iris", project="acme")
notify("Build failed", subject="CI failure", priority="high", sender="hephaestus", project="nore", details="Error log here")
```

## CLI

```bash
python3 studio/notifier.py "Deploy complete" \
    --priority normal \
    --sender iris \
    --project acme
```

## Parameters

| Parameter | Values | Description |
|---|---|---|
| `message` | string | Main message body |
| `subject` | string | Bold header (optional — defaults to message) |
| `priority` | `low` `normal` `high` `urgent` | Controls emoji and `<!channel>` ping |
| `sender` | agent name | Shown as emoji + name in message footer |
| `project` | prefix string | Project tag shown in footer |
| `details` | string | Rendered as a code block below the message |

## Priority behaviour

- `urgent` — sends `<!channel>` ping
- `high` — dispatched immediately by `postman.py` at send time (doesn't wait for sweep)
- `normal` / `low` — dispatched on next postman sweep

## Sender emoji mapping

| Sender | Emoji |
|---|---|
| hephaestus | 🔨 |
| athena | 🦉 |
| hermes | ⚡ |
| financial-review | 💶 |
| iris | 🌈 |
| themis | ⚖️ |
| aphrodite | 🎨 |
| abderus | ⏳ |

## Required env var

`SLACK_WEBHOOK_URL` — set in `studio/.env`. If not set, notifications are silently skipped.

## Related

- [postman.md](postman.md) — async message queue that uses notifier for dispatch
