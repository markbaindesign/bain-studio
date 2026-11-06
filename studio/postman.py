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
import subprocess
import argparse
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

LOG_FILE = Path(__file__).resolve().parent / 'postman.log'


def _log(event: str, **fields):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    parts = [f"[{ts}] {event}"] + [f"{k}={v}" for k, v in fields.items() if v]
    with LOG_FILE.open('a') as f:
        f.write(' '.join(parts) + '\n')

load_dotenv(Path(__file__).resolve().parent / '.env')

STUDIO_ROOT   = Path(__file__).resolve().parents[1]
SCAN_ROOTS    = [Path(p) for p in os.getenv('STUDIO_SCAN_ROOTS', '').split(':') if p]
VALID_TYPES   = {'event', 'handoff', 'alert', 'report', 'note'}
VALID_PRIORITIES = {'low', 'normal', 'high', 'urgent'}


# ---------------------------------------------------------------------------
# Inbox resolution
# ---------------------------------------------------------------------------

def _studio_inbox() -> Path:
    inbox = STUDIO_ROOT / 'studio' / 'inbox'
    inbox.mkdir(parents=True, exist_ok=True)
    return inbox


def _registry_path(project: str):
    """Project path for a registered prefix (e.g. ASP).

    Asks studio/registry.py, which reads the registry outside this repo and
    falls back to docs/projects/*.md while that migration is in progress.
    See ADR 021 and BSTD-875.
    """
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import registry as _registry
        return _registry.path_for(project, repo_root=STUDIO_ROOT)
    except Exception:
        # Never let identity resolution take postman down: fall back to the
        # frontmatter scan this function used to do.
        for doc in (STUDIO_ROOT / 'docs' / 'projects').glob('*.md'):
            meta, _ = _parse_message(doc)
            if meta.get('prefix', '').upper() == project.upper() and meta.get('path'):
                return Path(meta['path'])
        return None


def _project_inbox(project: str):
    """Find .claude/inbox/ for a project: registry prefix first, then by walking STUDIO_SCAN_ROOTS."""
    registered = _registry_path(project)
    if registered and registered.resolve() == STUDIO_ROOT.resolve():
        return _studio_inbox()
    if registered and registered.is_dir():
        inbox = registered / '.claude' / 'inbox'
        inbox.mkdir(parents=True, exist_ok=True)
        return inbox
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
    # Also try `to` as a project slug so `to: studio` routes to
    # bain-studio/.claude/inbox rather than the postman's own inbox dir
    if to:
        to_inbox = _project_inbox(to)
        if to_inbox:
            return to_inbox
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
    _log('SEND', id=msg_id, from_=sender, to=to, project=project, priority=priority, subject=subject)

    # Immediate Slack alert for high/urgent
    if priority in ('high', 'urgent'):
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from notifier import notify
            posted = notify(
                body or subject,
                subject=subject,
                priority=priority,
                sender=sender,
                project=project,
            )
            # Posted now, so the sweep must not post it again. If it failed, the sweep retries.
            if posted:
                _stamp_notified(dest)
        except Exception as e:
            print(f'[postman] Slack notify failed: {e}', file=sys.stderr)

    try:
        panes = ping(inbox, subject=subject, sender=sender, project=project)
        _log('PING', id=msg_id, panes=','.join(panes) or 'none')
        if not panes:
            print('[postman] no live Claude session for that inbox; message waits for /check-inbox',
                  file=sys.stderr)
    except Exception as e:
        print(f'[postman] ping failed: {e}', file=sys.stderr)

    return dest


# ---------------------------------------------------------------------------
# Ping — tell the live Claude session(s) that own an inbox that mail arrived
# ---------------------------------------------------------------------------

MAIL_MARK = '📬 '


def _tmux(*args) -> str:
    return subprocess.run(['tmux', *args], capture_output=True, text=True, timeout=5).stdout


def _project_root(inbox: Path) -> Path:
    """The project directory an inbox belongs to (.claude/inbox and studio/inbox both sit two levels down)."""
    return inbox.resolve().parent.parent


def _claude_panes(root: Path):
    """tmux panes running Claude Code with a working directory at or under `root`."""
    out = _tmux('list-panes', '-a', '-F',
                '#{pane_id}\t#{pane_tty}\t#{pane_current_command}\t#{pane_current_path}\t#{window_id}')
    panes = []
    for line in out.splitlines():
        parts = line.split('\t')
        if len(parts) != 5 or parts[2] != 'claude':
            continue
        path = Path(parts[3]).resolve()
        if path == root or root in path.parents:
            panes.append({'id': parts[0], 'tty': parts[1], 'window': parts[4]})
    return panes


def mark_window(window: str):
    """Prefix the window name with 📬, remembering the original so unmark can restore it."""
    name, auto = _tmux('display-message', '-p', '-t', window,
                       '#{window_name}\t#{automatic-rename}').strip().partition('\t')[::2]
    if name.startswith(MAIL_MARK):
        return
    _tmux('set-option', '-w', '-t', window, '@postman_name', name)
    _tmux('set-option', '-w', '-t', window, '@postman_auto', auto)
    _tmux('rename-window', '-t', window, MAIL_MARK + name)


def unmark_window(window: str):
    """Undo mark_window: restore the name, and automatic-rename if the window had it on."""
    name = _tmux('show-options', '-wqv', '-t', window, '@postman_name').strip()
    if not name:
        return
    auto = _tmux('show-options', '-wqv', '-t', window, '@postman_auto').strip()
    _tmux('rename-window', '-t', window, name)
    if auto == '1':
        _tmux('set-option', '-wu', '-t', window, 'automatic-rename')
    _tmux('set-option', '-wu', '-t', window, '@postman_name')
    _tmux('set-option', '-wu', '-t', window, '@postman_auto')


def ping(inbox: Path, *, subject: str, sender: str = '', project: str = '') -> list:
    """
    Alert every live Claude session working in the inbox's project: ring the pane's bell,
    mark its tmux window 📬, flash a message on attached tmux clients, and send a desktop
    notification. Claude itself sees the message on its next turn via the inbox-alert hook.
    Returns the ids of the panes alerted. Never raises for a missing tmux or notify-send.
    """
    if os.getenv('POSTMAN_NO_PING'):
        return []
    try:
        panes = _claude_panes(_project_root(inbox))
    except (OSError, subprocess.SubprocessError):
        panes = []
    label = f"{MAIL_MARK}{project or _project_root(inbox).name}: {subject} (from {sender})"
    for pane in panes:
        try:
            with open(pane['tty'], 'w') as tty:
                tty.write('\a')
        except OSError:
            pass
        mark_window(pane['window'])
    if panes:
        for client in _tmux('list-clients', '-F', '#{client_name}').split():
            _tmux('display-message', '-d', '8000', '-c', client, label)
    try:
        subprocess.run(['notify-send', '-u', 'critical', 'Postman', label],
                       capture_output=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        pass
    return [p['id'] for p in panes]


# ---------------------------------------------------------------------------
# Sweep (Hermes)
# ---------------------------------------------------------------------------

def sweep(dry_run: bool = False) -> int:
    """
    Scan all inboxes and post each message to Slack once, stamping it `notified_at`.

    Messages stay in the inbox: archiving is done by /check-inbox once a session has
    actually read them. (Until 2026-09-17 the sweep archived everything, so messages were
    gone before any session saw them.) High/urgent messages sent via send() are stamped at
    send time; hand-written message files carry no stamp and get notified here whatever
    their priority.
    Returns count of messages notified.
    """
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from notifier import notify
    except ImportError:
        notify = None

    dispatched = 0
    for inbox in _find_all_inboxes():
        for msg_path in sorted(inbox.glob('msg-*.md')):
            meta, body = _parse_message(msg_path)
            if not meta or meta.get('notified_at'):
                continue

            if dry_run:
                print(f'[dry-run] would notify: {msg_path.name} — {meta.get("subject", "")}')
                dispatched += 1
                continue

            # Left unstamped on failure, so the next sweep retries it
            if not notify:
                print('[postman] notifier unavailable; nothing posted', file=sys.stderr)
                return dispatched
            posted = notify(
                body.strip() or meta.get('subject', ''),
                subject=meta.get('subject', ''),
                priority=meta.get('priority', 'normal'),
                sender=meta.get('from', 'studio'),
                project=meta.get('project', ''),
            )
            if not posted:
                print(f'[postman] Slack notify failed for {msg_path.name}', file=sys.stderr)
                continue
            _stamp_notified(msg_path)
            _log('NOTIFY', id=msg_path.stem, from_=meta.get('from', ''), to=meta.get('to', ''),
                 project=meta.get('project', ''), priority=meta.get('priority', ''), subject=meta.get('subject', ''))
            dispatched += 1

    return dispatched


def _stamp_notified(path: Path):
    """Add `notified_at` as the last frontmatter line."""
    text = path.read_text()
    if not text.startswith('---'):
        return
    close = text.find('\n---', 3)
    if close == -1:
        return
    stamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
    path.write_text(text[:close] + f'\nnotified_at: {stamp}' + text[close:])


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


def _cmd_unmark(args):
    pane = args.pane or os.getenv('TMUX_PANE')
    if not pane:
        print('[postman] not in tmux and no --pane given', file=sys.stderr)
        return
    unmark_window(_tmux('display-message', '-p', '-t', pane, '#{window_id}').strip())


def _cmd_log(args):
    if not LOG_FILE.exists():
        print('[postman] no log yet')
        return
    lines = LOG_FILE.read_text().splitlines()
    for line in lines[-args.n:]:
        print(line)


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

    p_sweep = sub.add_parser('sweep', help='Post not-yet-notified messages to Slack (does not archive)')
    p_sweep.add_argument('--dry-run', action='store_true',      help='Print without dispatching')
    p_sweep.set_defaults(func=_cmd_sweep)

    p_unmark = sub.add_parser('unmark', help='Remove the 📬 marker from a tmux window')
    p_unmark.add_argument('--pane', default='',               help='tmux pane id (default: $TMUX_PANE)')
    p_unmark.set_defaults(func=_cmd_unmark)

    p_log = sub.add_parser('log', help='Show recent postman activity')
    p_log.add_argument('-n', type=int, default=20,              help='Number of lines to show')
    p_log.set_defaults(func=_cmd_log)

    args = parser.parse_args()
    args.func(args)
