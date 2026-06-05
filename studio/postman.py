#!/usr/bin/env python3
"""
Studio Postman — async message passing between agents and projects.

Send a message:
    from studio.postman import send
    send(to='studio', subject='Build failed', body='Details here',
         sender='hephaestus', project='nore', priority='high')

    # or CLI:
    python3 studio/postman.py send --to studio --subject "Build failed" \
        --body "Details here" --sender hephaestus --project nore --priority high

Sweep (run by Hermes):
    python3 studio/postman.py sweep
"""

import os
import sys
import uuid
import argparse
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / '.env')

STUDIO_ROOT   = Path(__file__).resolve().parents[1]
SCAN_ROOTS    = [Path(p) for p in os.getenv('STUDIO_SCAN_ROOTS', '').split(':') if p]
VALID_TYPES   = {'event', 'handoff', 'alert', 'report'}
VALID_PRIORITIES = {'low', 'normal', 'high', 'urgent'}


# ---------------------------------------------------------------------------
# Inbox resolution
# ---------------------------------------------------------------------------

def _studio_inbox() -> Path:
    inbox = STUDIO_ROOT / 'studio' / 'inbox'
    inbox.mkdir(parents=True, exist_ok=True)
    return inbox


def _project_inbox(project: str):
    """Find .claude/inbox/ for a project by walking STUDIO_SCAN_ROOTS."""
    slug = project.lower()
    for root in SCAN_ROOTS:
        for candidate in root.rglob('.claude/inbox'):
            if candidate.is_dir() and slug in str(candidate.parent.parent).lower():
                return candidate
    return None


def _resolve_inbox(to: str, project: str) -> Path:
    """Return the inbox Path for the given recipient."""
    # Project-addressed messages go to the project inbox if found
    if project:
        proj_inbox = _project_inbox(project)
        if proj_inbox:
            return proj_inbox
    return _studio_inbox()


def _find_all_inboxes():
    """Walk STUDIO_SCAN_ROOTS and find all .claude/inbox/ directories."""
    inboxes = [_studio_inbox()]
    seen = {inboxes[0].resolve()}
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for candidate in root.rglob('.claude/inbox'):
            resolved = candidate.resolve()
            if candidate.is_dir() and resolved not in seen:
                inboxes.append(candidate)
                seen.add(resolved)
    return inboxes


# ---------------------------------------------------------------------------
# Send
# ---------------------------------------------------------------------------

def send(
    to: str,
    subject: str,
    body: str = '',
    *,
    sender: str = 'studio',
    project: str = '',
    msg_type: str = 'event',
    priority: str = 'normal',
) -> Path:
    """
    Write a message file to the appropriate inbox.
    Returns the path of the written file.
    """
    if msg_type not in VALID_TYPES:
        raise ValueError(f'type must be one of {VALID_TYPES}')
    if priority not in VALID_PRIORITIES:
        raise ValueError(f'priority must be one of {VALID_PRIORITIES}')

    msg_id  = f"msg-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}"
    sent_at = datetime.now(timezone.utc).isoformat(timespec='seconds')

    frontmatter = f"""---
id: {msg_id}
from: {sender}
project: {project or ''}
to: {to}
type: {msg_type}
subject: {subject}
priority: {priority}
sent_at: {sent_at}
---
"""
    content = frontmatter + (f"\n{body}\n" if body else '')

    inbox = _resolve_inbox(to, project)
    inbox.mkdir(parents=True, exist_ok=True)
    dest  = inbox / f"{msg_id}.md"
    dest.write_text(content)

    # Immediate Slack alert for high/urgent
    if priority in ('high', 'urgent'):
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from notifier import notify
            notify(
                body or subject,
                subject=subject,
                priority=priority,
                sender=sender,
                project=project,
            )
        except Exception as e:
            print(f'[postman] Slack notify failed: {e}', file=sys.stderr)

    return dest


# ---------------------------------------------------------------------------
# Sweep (Hermes)
# ---------------------------------------------------------------------------

def sweep(dry_run: bool = False) -> int:
    """
    Scan all inboxes, dispatch unprocessed messages via Slack, archive them.
    Returns count of messages dispatched.
    """
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from notifier import notify
    except ImportError:
        notify = None

    dispatched = 0
    for inbox in _find_all_inboxes():
        messages = sorted(inbox.glob('msg-*.md'))
        if not messages:
            continue

        processed_dir = inbox / 'processed'
        if not dry_run:
            processed_dir.mkdir(exist_ok=True)

        for msg_path in messages:
            meta, body = _parse_message(msg_path)
            if not meta:
                continue

            priority = meta.get('priority', 'normal')
            # Skip high/urgent — already dispatched at send time
            if priority in ('high', 'urgent'):
                if not dry_run:
                    msg_path.rename(processed_dir / msg_path.name)
                dispatched += 1
                continue

            if notify and not dry_run:
                notify(
                    body.strip() or meta.get('subject', ''),
                    subject=meta.get('subject', ''),
                    priority=priority,
                    sender=meta.get('from', 'studio'),
                    project=meta.get('project', ''),
                )

            if dry_run:
                print(f'[dry-run] would dispatch: {msg_path.name} — {meta.get("subject", "")}')
            else:
                msg_path.rename(processed_dir / msg_path.name)

            dispatched += 1

    return dispatched


def _parse_message(path: Path):
    """Parse YAML frontmatter + body from a message file."""
    try:
        text = path.read_text()
        if not text.startswith('---'):
            return {}, text
        parts = text.split('---', 2)
        if len(parts) < 3:
            return {}, text
        meta = {}
        for line in parts[1].strip().splitlines():
            if ':' in line:
                k, _, v = line.partition(':')
                meta[k.strip()] = v.strip()
        return meta, parts[2]
    except Exception:
        return {}, ''


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cmd_send(args):
    path = send(
        to=args.to,
        subject=args.subject,
        body=args.body,
        sender=args.sender,
        project=args.project,
        msg_type=args.type,
        priority=args.priority,
    )
    print(f'[postman] sent → {path}')


def _cmd_sweep(args):
    n = sweep(dry_run=args.dry_run)
    print(f'[postman] sweep complete — {n} message(s) dispatched')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Studio Postman')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_send = sub.add_parser('send', help='Send a message')
    p_send.add_argument('--to',       required=True,            help='Recipient (studio, mark, hephaestus, …)')
    p_send.add_argument('--subject',  required=True,            help='Message subject')
    p_send.add_argument('--body',     default='',               help='Message body (markdown)')
    p_send.add_argument('--sender',   default='studio',         help='Sending agent')
    p_send.add_argument('--project',  default='',               help='Project prefix')
    p_send.add_argument('--type',     default='event',          choices=list(VALID_TYPES))
    p_send.add_argument('--priority', default='normal',         choices=list(VALID_PRIORITIES))
    p_send.set_defaults(func=_cmd_send)

    p_sweep = sub.add_parser('sweep', help='Dispatch all pending messages')
    p_sweep.add_argument('--dry-run', action='store_true',      help='Print without dispatching')
    p_sweep.set_defaults(func=_cmd_sweep)

    args = parser.parse_args()
    args.func(args)
