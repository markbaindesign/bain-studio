#!/usr/bin/env python3
"""
Migrate qa/qa-log.md files from old table format to new event log format.

Old format:
    | ref | opened | description | status | closed |
    | BEA-QA-001 | 2026-06-19 | Some bug | passed | 2026-06-19 |

New format:
    [2026-06-19 00:00] BEA-QA-001 registered — Some bug
    [2026-06-19 00:00] BEA-QA-001 passed

Usage:
    python3 studio/migrate_qa_log.py              # dry run — shows what would change
    python3 studio/migrate_qa_log.py --apply      # apply changes
    python3 studio/migrate_qa_log.py --path /x/y  # specific directory
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / '.env')

SCAN_ROOTS = [Path(p) for p in os.getenv('STUDIO_SCAN_ROOTS', '').split(':') if p]
HEADER_TEMPLATE = """# QA Log — {prefix}

Append-only event log. One line per lifecycle event.
Format: [YYYY-MM-DD HH:MM] {{ref}} {{event}} — {{details}}

To check status of an item: grep {{ref}} qa/qa-log.md
To list open items: grep "registered" qa/qa-log.md | grep -v "passed\\|wontfix"

"""

TABLE_ROW_RE = re.compile(
    r'^\|\s*(?P<ref>[A-Z]+-QA-\d+)\s*\|\s*(?P<opened>\d{4}-\d{2}-\d{2})\s*\|'
    r'\s*(?P<desc>[^|]+?)\s*\|\s*(?P<status>open|passed|failed|wontfix)\s*\|'
    r'\s*(?P<closed>\S*)\s*\|'
)
HEADER_ROW_RE = re.compile(r'^\|\s*ref\s*\|')
ALREADY_MIGRATED_RE = re.compile(r'^\[?\d{4}-\d{2}-\d{2}')


def is_old_format(text: str) -> bool:
    for line in text.splitlines():
        if HEADER_ROW_RE.match(line):
            return True
        if ALREADY_MIGRATED_RE.match(line.strip()):
            return False
    return False


def extract_prefix(ref: str) -> str:
    parts = ref.split('-QA-')
    return parts[0] if parts else 'UNKNOWN'


def convert(path: Path) -> Optional[Tuple[str, str]]:
    text = path.read_text()

    if not is_old_format(text):
        return None

    lines = text.splitlines()
    events = []
    prefix = 'UNKNOWN'

    for line in lines:
        m = TABLE_ROW_RE.match(line)
        if not m:
            continue

        ref = m.group('ref')
        opened = m.group('opened')
        desc = m.group('desc').strip()
        status = m.group('status')
        closed = m.group('closed').strip()
        prefix = extract_prefix(ref)

        events.append(f"[{opened} 00:00] {ref} registered — {desc}")

        if status == 'passed' and closed:
            events.append(f"[{closed} 00:00] {ref} passed")
        elif status == 'wontfix' and closed:
            events.append(f"[{closed} 00:00] {ref} wontfix")
        # open / failed: no closing line

    if not events:
        return None

    note = "<!-- migrated from table format -->\n"
    new_text = HEADER_TEMPLATE.format(prefix=prefix) + note + '\n'.join(events) + '\n'
    return text, new_text


def find_logs(roots: List[Path]) -> List[Path]:
    found = []
    seen = set()
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob('qa/qa-log.md'):
            resolved = p.resolve()
            if resolved not in seen:
                seen.add(resolved)
                found.append(p)
    return sorted(found)


def main():
    parser = argparse.ArgumentParser(description='Migrate qa-log.md to event log format')
    parser.add_argument('--apply', action='store_true', help='Apply changes (default: dry run)')
    parser.add_argument('--path', help='Scan a specific directory instead of STUDIO_SCAN_ROOTS')
    args = parser.parse_args()

    roots = [Path(args.path)] if args.path else SCAN_ROOTS
    logs = find_logs(roots)

    if not logs:
        print('No qa-log.md files found.')
        return

    migrated = 0
    skipped = 0

    for log_path in logs:
        result = convert(log_path)
        if result is None:
            print(f'  SKIP  {log_path}  (already new format or no table rows)')
            skipped += 1
            continue

        old_text, new_text = result
        print(f'  {"APPLY" if args.apply else "DRY  "}  {log_path}')

        # Show diff summary
        old_lines = [l for l in old_text.splitlines() if TABLE_ROW_RE.match(l)]
        new_lines = [l for l in new_text.splitlines() if l.startswith('[')]
        print(f'         {len(old_lines)} table rows → {len(new_lines)} log events')

        if args.apply:
            log_path.write_text(new_text)

        migrated += 1

    print()
    if args.apply:
        print(f'Done. {migrated} migrated, {skipped} already up to date.')
    else:
        print(f'Dry run. {migrated} would be migrated, {skipped} already up to date.')
        print('Run with --apply to make changes.')


if __name__ == '__main__':
    main()
