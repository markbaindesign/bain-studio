---
command: python3 studio/postman.py
description: Routes messages from agents into project .claude/inbox/ directories
god: hermes
tags:
- tool
---

# postman.py — Inter-Agent Messaging

Async message passing between agents and projects. Messages are written to inbox directories as markdown files and dispatched to Slack on sweep.

## Python API

```python
from studio.postman import send

send(
    to='studio',
    subject='Build failed on ACME',
    body='Details of the failure here.',
    sender='hephaestus',
    project='acme',
    priority='high',
)
```

## CLI

```bash
# Send a message
python3 studio/postman.py send \
    --to studio \
    --subject "Build failed" \
    --body "Details here" \
    --sender hephaestus \
    --project acme \
    --priority high

# Sweep and dispatch all pending messages
python3 studio/postman.py sweep
python3 studio/postman.py sweep --dry-run
```

## Parameters

| Parameter | Values | Description |
|---|---|---|
| `to` | `studio`, agent name, project | Recipient |
| `subject` | string | Message subject |
| `body` | markdown string | Message body |
| `sender` | agent name | Who sent it |
| `project` | prefix string | Associated project |
| `type` | `event` `handoff` `alert` `report` | Message classification |
| `priority` | `low` `normal` `high` `urgent` | Dispatch urgency |

## Inbox locations

- **Studio inbox:** `studio/inbox/` in the bain-studio repo
- **Project inbox:** `{project}/.claude/inbox/` — resolved by walking `STUDIO_SCAN_ROOTS`

`STUDIO_SCAN_ROOTS` is set in `studio/.env` as a colon-separated list of directory roots to scan.

## Message lifecycle

1. `send()` writes a `msg-{timestamp}-{id}.md` file to the appropriate inbox
2. High/urgent messages trigger an immediate Slack notification via `notifier.py`
3. On sweep, remaining messages are dispatched to Slack and moved to `inbox/processed/`

## Sweep

Run by Hermes as part of the studio startup routine. Can also be triggered manually:

```bash
cd ~/code/bain-studio && python3 studio/postman.py sweep
```

## Related

- [notifier.md](notifier.md) — Slack dispatch used internally by postman
