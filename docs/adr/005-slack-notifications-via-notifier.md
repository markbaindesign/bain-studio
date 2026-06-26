# ADR 005 — Slack notifications go through notifier.py, not direct webhook

**Date:** 2026-06-15
**Status:** Accepted

## Decision

No project or agent sends messages to the Slack webhook URL directly. All Slack notifications are dispatched by calling `studio/notifier.py` (or importing `studio.notifier.notify()`).

## Context

The studio has a Slack incoming webhook (`SLACK_WEBHOOK_URL` in `studio/.env`, channel `#alerts`). Multiple projects and agents need to send notifications. The question is whether each project should hold a copy of the webhook URL or delegate to a single point of dispatch.

## Reasoning

- **Single ownership:** The webhook URL lives only in `studio/.env`. When it rotates, one file changes — not N project `.env` files.
- **Consistent formatting:** `notifier.py` handles priority levels, emoji, sender tagging, and `<!channel>` pings. Every caller gets the same message shape automatically.
- **Abstraction layer:** Projects don't need to know the transport (Slack today, something else tomorrow). They call `notify()` and the studio handles routing.
- **Python `dotenv` limitation:** Project `.env` files cannot source other files — so sharing via a `source` directive is not portable.

## Pattern

Any project or agent that needs to send a notification calls the studio notifier:

**CLI (from any directory):**
```bash
python3 /media/data/dev/bain-studio/studio/notifier.py "Deploy complete" \
    --priority normal \
    --sender hephaestus \
    --project NORE
```

**Python import:**
```python
import sys
sys.path.insert(0, '/media/data/dev/bain-studio')
from studio.notifier import notify

notify("Deploy complete", priority="normal", sender="hephaestus", project="NORE")
```

`notifier.py` loads `studio/.env` itself — callers need no knowledge of the webhook URL.

## Consequences

- Projects must know the path to the studio repo. This is acceptable: all active projects are registered in `studio/projects.json` and the studio path is stable (`/media/data/dev/bain-studio`).
- If the studio repo moves, callers need updating. Mitigated by keeping the path in an env var (`STUDIO_DIR`) if needed in future.
- `notifier.py` is a shared dependency — changes to its interface affect all callers. Keep the `notify()` signature stable; extend via optional kwargs only.

## Related

- [ADR 002](002-bainbot-asana-token.md) — same principle for Asana: mutations go through a single authorised path, not distributed credentials
- `docs/utilities/notifier.md` — full notifier reference
