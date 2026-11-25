---
name: project-watcher
description: Watch a project so DevBot answers Mark's Asana comments and assignments on its bot tasks within about a minute. A Claude session in the project watches it already; this is the manual switch. Usage /project-watcher PREFIX, /project-watcher stop PREFIX, /project-watcher status.
---

# /project-watcher

A shortcut for the webhook listener's watch commands. All logic is in the script; this skill
only runs it. Opening a Claude session in a project already watches it (session hooks), so this
is for watching one you are not in, or stopping a watch.

| Mark types | Run |
|---|---|
| `/project-watcher PREFIX` | `python3 /media/data/dev/bain-studio/studio/asana_webhook.py watch PREFIX` |
| `/project-watcher stop PREFIX` | `python3 /media/data/dev/bain-studio/studio/asana_webhook.py unwatch PREFIX` |
| `/project-watcher inbox on` / `inbox off` | `python3 /media/data/dev/bain-studio/studio/asana_webhook.py inbox on` (or `off`): DevBot's tasks in every project, polled every 3 minutes |
| `/project-watcher status` (or no argument) | `python3 /media/data/dev/bain-studio/studio/asana_webhook.py status` |

With no prefix and a project `CLAUDE.md` in the current directory, use its `ASANA_TASK_PREFIX`.

Report the script's output in one or two lines. If it says the listener is down, give Mark the
command it prints; do not start the service or Tailscale Funnel yourself.

Full reference: `/media/data/dev/bain-studio/docs/utilities/asana-webhook.md`.
