#!/usr/bin/env python3
# Put unread postman mail in front of Claude, so a message doesn't sit in an inbox until
# someone happens to run /check-inbox (KF's bd-search notes did, 2026-10-21).
#
# UserPromptSubmit / SessionStart: if the session's project inbox holds msg-*.md files,
# add a summary of them to Claude's context.
# Any event: once the inbox is empty, clear the 📬 marker postman put on this tmux window.
#
# Versioned at bain-studio/.claude/hooks/inbox-alert.py; symlinked into ~/.claude/hooks and
# referenced from ~/.claude/settings.json and ~/.claude-kf/settings.json so it fires in any cwd.

import json
import os
import sys
from pathlib import Path

STUDIO = Path(__file__).resolve().parents[2] / 'studio'


def project_root(cwd: Path):
    """Nearest directory at or above cwd that has a .claude/inbox (or, for bain-studio, a studio/inbox)."""
    for d in [cwd, *cwd.parents]:
        if (d / '.claude' / 'inbox').is_dir() or (d / 'studio' / 'inbox').is_dir():
            return d
    return None


def unread(root: Path):
    inboxes = [root / '.claude' / 'inbox', root / 'studio' / 'inbox']
    return sorted((p for i in inboxes if i.is_dir() for p in i.glob('msg-*.md')), key=lambda p: p.name)


def meta(path: Path) -> dict:
    fields = {}
    try:
        head = path.read_text().split('---', 2)[1]
    except (OSError, IndexError):
        return fields
    for line in head.strip().splitlines():
        k, _, v = line.partition(':')
        fields[k.strip()] = v.strip()
    return fields


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return
    root = project_root(Path(event.get('cwd') or os.getcwd()))
    msgs = unread(root) if root else []

    if not msgs:
        if os.getenv('TMUX_PANE'):
            sys.path.insert(0, str(STUDIO))
            try:
                import postman
                window = postman._tmux('display-message', '-p', '-t', os.environ['TMUX_PANE'], '#{window_id}').strip()
                postman.unmark_window(window)
            except Exception:
                pass
        return

    name = event.get('hook_event_name', '')
    if name not in ('UserPromptSubmit', 'SessionStart'):
        return
    lines = [f"📬 {len(msgs)} unread postman message(s) for this project:"]
    for p in msgs:
        m = meta(p)
        lines.append(f"- [{m.get('priority', 'normal')}] {m.get('subject', p.stem)} "
                     f"(from {m.get('from', '?')}, {m.get('sent_at', '?')}) {p}")
    lines.append("Tell Mark about these at the top of your reply. Run /check-inbox to read and "
                 "archive them, before the current request if any is high/urgent priority, "
                 "otherwise once the current request is done.")
    print(json.dumps({'hookSpecificOutput': {'hookEventName': name,
                                             'additionalContext': '\n'.join(lines)}}))


if __name__ == '__main__':
    main()
