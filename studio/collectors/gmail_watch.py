#!/usr/bin/env python3
"""
Gmail signal collector for Hermes.

Invokes a headless Claude session (with Gmail MCP) to scan for new client
signals and write them as structured .md files to studio/inbox/.

Run on cron, e.g.:
  */30 * * * * cd /media/data/dev/bain-studio && python3 studio/collectors/gmail_watch.py >> studio/collectors/gmail_watch.log 2>&1
"""

import subprocess
import json
import datetime
import sys
from pathlib import Path

STUDIO_DIR = Path(__file__).parent.parent
INBOX_DIR = STUDIO_DIR / "inbox"
STATE_FILE = STUDIO_DIR / ".gmail_state.json"
LOG_PREFIX = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] gmail_watch"


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"processed_thread_ids": [], "last_run": None}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def build_prompt(processed_ids, today):
    inbox_path = str(INBOX_DIR)
    skip_clause = ""
    if processed_ids:
        # Only pass recent IDs to keep prompt size reasonable
        recent_ids = processed_ids[-100:]
        skip_clause = f"\n\nSkip these thread IDs (already processed): {json.dumps(recent_ids)}"

    return f"""You are a Gmail signal collector for a freelance web development studio. Today is {today}.

Search Gmail for potential client signals using this query:
  `is:unread category:primary newer_than:2d`

For each thread returned:
1. Read the thread content
2. Classify it — skip newsletters, automated notifications, order receipts, and obvious spam
3. If it looks like a genuine signal (RFQ, support request, referral intro, or general enquiry), write it to inbox

Write each signal as a file at: `{inbox_path}/{{thread_id}}.md`

Use this exact format:
---
thread_id: {{thread_id}}
from: {{sender name and email}}
subject: {{subject}}
date: {{received date, ISO format}}
signal_type: {{RFQ | Support | Referral | General | Spam}}
status: pending
---

# {{subject}}

**From:** {{sender name and email}}
**Date:** {{received date}}

{{message body — up to 1000 characters}}

After processing all threads, output one final line in this exact format (no other text after it):
PROCESSED_IDS::{{json array of thread_id strings you wrote to inbox}}

If no signals were found, output:
PROCESSED_IDS::[]
{skip_clause}"""


def run_collector(processed_ids):
    today = datetime.date.today().isoformat()
    prompt = build_prompt(processed_ids, today)

    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json"],
        capture_output=True,
        text=True,
        cwd=str(STUDIO_DIR),
    )

    if result.returncode != 0:
        print(f"{LOG_PREFIX} ERROR: claude exited {result.returncode}: {result.stderr[:200]}", file=sys.stderr)
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"{LOG_PREFIX} ERROR: could not parse claude output", file=sys.stderr)
        return []

    if data.get("is_error"):
        print(f"{LOG_PREFIX} ERROR: {data.get('result', '')[:200]}", file=sys.stderr)
        return []

    response_text = data.get("result", "")
    new_ids = []
    for line in response_text.splitlines():
        line = line.strip()
        if line.startswith("PROCESSED_IDS::"):
            try:
                new_ids = json.loads(line[len("PROCESSED_IDS::"):].strip())
            except json.JSONDecodeError:
                print(f"{LOG_PREFIX} WARNING: could not parse PROCESSED_IDS line", file=sys.stderr)
            break

    return new_ids


def main():
    INBOX_DIR.mkdir(exist_ok=True)
    state = load_state()
    processed_ids = list(state.get("processed_thread_ids", []))

    print(f"{LOG_PREFIX}: starting ({len(processed_ids)} threads already seen)")

    new_ids = run_collector(processed_ids)

    added = [tid for tid in new_ids if tid not in processed_ids]
    if added:
        for tid in added:
            processed_ids.append(tid)
            print(f"{LOG_PREFIX}: new signal → inbox/{tid}.md")
    else:
        print(f"{LOG_PREFIX}: no new signals")

    state["processed_thread_ids"] = processed_ids
    state["last_run"] = datetime.datetime.now().isoformat()
    save_state(state)

    print(f"{LOG_PREFIX}: done")


if __name__ == "__main__":
    main()
