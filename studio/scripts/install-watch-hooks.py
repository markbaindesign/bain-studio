#!/usr/bin/env python3
"""Add the project-watcher session hooks to Claude's user settings (BSTD-894).

    python3 studio/scripts/install-watch-hooks.py            # show what would change
    python3 studio/scripts/install-watch-hooks.py --apply    # write it

Adds a SessionStart and a SessionEnd hook that run `asana_webhook.py session-start`
and `session-end` from the checkout this script lives in, so run it from the one the
listener runs from (the ops deploy). Covers ~/.claude and ~/.claude-kf, the second
config dir ADR 017 gives the KF account. Idempotent: a hook already present is left
alone, and nothing else in the file is touched.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

WEBHOOK = Path(__file__).resolve().parents[1] / "asana_webhook.py"
CONFIG_DIRS = [Path.home() / ".claude", Path.home() / ".claude-kf"]
EVENTS = {"SessionStart": "session-start", "SessionEnd": "session-end"}


def hook_command(sub: str, webhook: Path = WEBHOOK) -> str:
    return f"python3 {webhook} {sub} >/dev/null 2>&1; exit 0"


def add_hooks(settings: dict, webhook: Path = WEBHOOK) -> list:
    """Add any missing session hook to `settings` in place; return the events added.
    A hook counts as present when some command already runs `asana_webhook.py {sub}`,
    from whichever checkout."""
    added = []
    hooks = settings.setdefault("hooks", {})
    for event, sub in EVENTS.items():
        groups = hooks.setdefault(event, [])
        present = any(f"asana_webhook.py {sub}" in (h.get("command") or "")
                      for g in groups for h in g.get("hooks") or [])
        if present:
            continue
        # async: the hook imports sync.py and reads the registry, and a session
        # should never wait on that to open.
        groups.append({"hooks": [{"type": "command", "command": hook_command(sub, webhook),
                                  "async": True}]})
        added.append(event)
    return added


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write the settings files")
    args = ap.parse_args()
    for cfg in CONFIG_DIRS:
        path = cfg / "settings.json"
        if not path.exists():
            print(f"{path}: not present, skipped")
            continue
        settings = json.loads(path.read_text())
        added = add_hooks(settings)
        if not added:
            print(f"{path}: hooks already present")
        elif args.apply:
            path.write_text(json.dumps(settings, indent=2) + "\n")
            print(f"{path}: added {', '.join(added)}")
        else:
            print(f"{path}: would add {', '.join(added)} (run with --apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
