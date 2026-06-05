#!/usr/bin/env python3
"""
Studio Notifier — sends alerts to Slack.

Usage:
    from studio.notifier import notify
    notify("Build failed on NORE", priority="high", sender="hephaestus", project="nore")

    # or from CLI:
    python3 studio/notifier.py "Deploy complete" --priority normal --sender iris --project mcf
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / '.env')

WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')

PRIORITY_EMOJI = {
    'urgent': ':rotating_light:',
    'high':   ':warning:',
    'normal': ':studio_microphone:',
    'low':    ':information_source:',
}

SENDER_EMOJI = {
    'hephaestus': ':hammer_and_wrench:',
    'athena':     ':owl:',
    'hermes':     ':zap:',
    'plutus':     ':euro:',
    'iris':       ':rainbow:',
    'themis':     ':scales:',
    'aphrodite':  ':art:',
    'abderus':    ':hourglass:',
}


def notify(
    message: str,
    *,
    subject: str = '',
    priority: str = 'normal',
    sender: str = 'studio',
    project: str = '',
    details: str = '',
) -> bool:
    """
    Send a Slack notification.
    Returns True on success, False on failure (never raises).
    """
    if not WEBHOOK_URL:
        print('[notifier] SLACK_WEBHOOK_URL not set — skipping', file=sys.stderr)
        return False

    emoji   = PRIORITY_EMOJI.get(priority, ':studio_microphone:')
    s_emoji = SENDER_EMOJI.get(sender.lower(), ':robot_face:')
    ts      = datetime.now().strftime('%H:%M')

    header = f"{emoji} *{subject or message}*" if subject else f"{emoji} {message}"
    meta   = f"{s_emoji} `{sender}`"
    if project:
        meta += f"  ›  :file_folder: `{project.upper()}`"
    meta += f"  ›  {ts}"

    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": header}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": meta}]},
    ]

    if subject and message != subject:
        blocks.insert(1, {"type": "section", "text": {"type": "mrkdwn", "text": message}})

    if details:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"```{details}```"}})

    if priority == 'urgent':
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "<!channel>"}})

    try:
        r = requests.post(WEBHOOK_URL, json={"blocks": blocks}, timeout=5)
        return r.status_code == 200
    except Exception as e:
        print(f'[notifier] Slack error: {e}', file=sys.stderr)
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Send a studio Slack notification')
    parser.add_argument('message',            help='Message body')
    parser.add_argument('--subject',          default='',       help='Bold header (optional)')
    parser.add_argument('--priority',         default='normal', choices=['low','normal','high','urgent'])
    parser.add_argument('--sender',           default='studio', help='Sending agent/god name')
    parser.add_argument('--project',          default='',       help='Project prefix (e.g. NORE)')
    parser.add_argument('--details',          default='',       help='Code block detail text')
    args = parser.parse_args()

    ok = notify(
        args.message,
        subject=args.subject,
        priority=args.priority,
        sender=args.sender,
        project=args.project,
        details=args.details,
    )
    sys.exit(0 if ok else 1)
