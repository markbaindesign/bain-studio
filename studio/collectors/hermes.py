#!/usr/bin/env python3
"""
Hermes — the studio orchestrator.

Watches studio/inbox/ for pending signals and routes each one through triage.
Run on cron after gmail_watch.py, or any time signals land in inbox/.

Cron example (runs 5 min after gmail_watch):
  5,35 * * * * cd /media/data/dev/bain-studio && python3 studio/collectors/hermes.py >> studio/collectors/hermes.log 2>&1
"""

import subprocess
import json
import datetime
import re
import sys
from pathlib import Path

# studio/collectors/ -> studio/ -> project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
INBOX_DIR = PROJECT_ROOT / "studio" / "inbox"
SKILL_PATH = Path.home() / ".claude/skills/triage/SKILL.md"
LOG_PREFIX = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] hermes"


def parse_signal(path):
    """Return (meta dict, body str) from an inbox .md file."""
    text = path.read_text()
    meta = {}
    body = text

    if text.startswith("---"):
        match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
        if match:
            for line in match.group(1).splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip()
            body = match.group(2).strip()

    return meta, body


def mark_processed(path, verdict):
    text = path.read_text()
    text = re.sub(r"^status: pending$", f"status: processed\nverdict: {verdict}", text, flags=re.MULTILINE)
    path.write_text(text)


def load_skill():
    if not SKILL_PATH.exists():
        return ""
    content = SKILL_PATH.read_text()
    # Strip YAML frontmatter
    if content.startswith("---"):
        match = re.match(r"^---\n.*?\n---\n(.*)", content, re.DOTALL)
        if match:
            return match.group(1).strip()
    return content


def prefilter(meta, body):
    """Cheap check: is this worth full triage? Returns (worth_triaging: bool, reason: str).

    Uses a minimal prompt — no skill loaded, no file I/O — so it costs ~$0.01.
    Skips full triage for automated notifications, newsletters, and obvious spam.
    """
    signal_block = f"""Subject: {meta.get('subject', '')}
From: {meta.get('from', '')}

{body[:400]}"""

    prompt = f"""You are a spam filter for a freelance web development studio inbox.

Classify this email as either SIGNAL or SKIP.

SIGNAL = a human wrote this and it could be: a project enquiry, a client request, a referral, or a support question.
SKIP   = automated notification, newsletter, job board alert, receipt, calendar invite, or obvious spam.

Email:
{signal_block}

Reply with exactly one word: SIGNAL or SKIP"""

    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )

    if result.returncode != 0:
        # On error, allow through — better to over-triage than miss a real lead
        return True, f"prefilter error (allowing through): {result.stderr[:80]}"

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return True, "prefilter parse error (allowing through)"

    answer = data.get("result", "").strip().upper()
    cost = data.get("total_cost_usd", 0)

    if "SKIP" in answer:
        return False, f"prefilter: SKIP (${cost:.3f})"
    return True, f"prefilter: SIGNAL (${cost:.3f})"


def triage_signal(meta, body):
    """Invoke a headless Claude session to run full triage. Returns (verdict, cost, error)."""
    skill = load_skill()

    signal_block = f"""From: {meta.get('from', 'Unknown')}
Subject: {meta.get('subject', '(no subject)')}
Date: {meta.get('date', 'Unknown')}

{body}"""

    prompt = f"""You are running the Autolycus triage process for Bain Design studio.

{skill}

---

Signal to triage:

{signal_block}

After completing all triage steps (classify, check known client, qualify if RFQ, route, log to context/pipeline/triage-log.md), output one final line in this exact format:
VERDICT::{{Pursue|Investigate|Decline|Support|Referral|Spam}}"""

    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )

    if result.returncode != 0:
        return None, 0, f"claude exited {result.returncode}: {result.stderr[:120]}"

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None, 0, "could not parse claude output"

    if data.get("is_error"):
        return None, 0, f"claude error: {data.get('result', '')[:120]}"

    cost = data.get("total_cost_usd", 0)
    verdict = None
    for line in data.get("result", "").splitlines():
        if line.strip().startswith("VERDICT::"):
            verdict = line.strip()[len("VERDICT::"):].strip()
            break

    return verdict, cost, None


def find_pending():
    if not INBOX_DIR.exists():
        return []
    pending = []
    for path in sorted(INBOX_DIR.glob("*.md")):
        if "status: pending" in path.read_text():
            pending.append(path)
    return pending


def main():
    pending = find_pending()

    if not pending:
        print(f"{LOG_PREFIX}: inbox empty, nothing to route")
        return

    print(f"{LOG_PREFIX}: {len(pending)} pending signal(s)")

    ok = 0
    skipped = 0
    failed = 0
    total_cost = 0.0

    for signal_path in pending:
        print(f"{LOG_PREFIX}: checking {signal_path.name} …")
        meta, body = parse_signal(signal_path)

        worth_triaging, prefilter_reason = prefilter(meta, body)
        print(f"{LOG_PREFIX}:   {prefilter_reason}")

        if not worth_triaging:
            mark_processed(signal_path, "Spam")
            skipped += 1
            continue

        verdict, cost, error = triage_signal(meta, body)
        total_cost += cost

        if error:
            print(f"{LOG_PREFIX}:   ERROR — {error}", file=sys.stderr)
            failed += 1
            continue

        verdict = verdict or "Unknown"
        mark_processed(signal_path, verdict)
        print(f"{LOG_PREFIX}:   → {verdict} (${cost:.3f})")
        ok += 1

    print(f"{LOG_PREFIX}: done — {ok} triaged, {skipped} skipped, {failed} failed — total ${total_cost:.3f}")


if __name__ == "__main__":
    main()
