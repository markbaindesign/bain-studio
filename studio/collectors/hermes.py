#!/usr/bin/env python3
"""
Hermes — the studio orchestrator.

Watches studio/inbox/ for pending signals and routes each one through triage.
Run on cron after gmail_watch.py, or any time signals land in inbox/.

Cron example (runs 5 min after gmail_watch):
  5 8 * * * cd /media/data/dev/bain-studio && python3 studio/collectors/hermes.py >> studio/collectors/hermes.log 2>&1
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
ATHENA_SKILL_PATH = Path.home() / ".claude/skills/athena/SKILL.md"
PLUTUS_SKILL_PATH = Path.home() / ".claude/skills/plutus/SKILL.md"
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


def create_brief_slug(meta):
    """Generate a slug from signal metadata. Returns slug string like 'client-project-2026-05-27'."""
    client = meta.get('from', 'unknown').split('@')[0].lower().replace(' ', '-')
    subject = meta.get('subject', 'project').lower()
    subject = re.sub(r'[^a-z0-9\s-]', '', subject)[:20].strip('-')

    today = datetime.datetime.now().strftime('%Y-%m-%d')
    slug = f"{client}-{subject}-{today}"
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug[:60]  # Reasonable filename limit


def create_brief_file(meta, body, slug):
    """Create a brief .md file from the signal. Returns the path."""
    brief_path = PROJECT_ROOT / "context" / "pipeline" / "briefs" / f"{slug}.md"
    brief_path.parent.mkdir(parents=True, exist_ok=True)

    channel = meta.get('channel', 'Unknown')
    client = meta.get('from', 'Unknown')
    project = meta.get('subject', 'Untitled')
    budget = meta.get('budget', 'Unknown')
    timeline = meta.get('timeline', 'Open')

    brief_content = f"""---
channel: {channel}
client: {client}
project: {project}
budget: {budget}
timeline: {timeline}
---

# Project description

{body}
"""

    brief_path.write_text(brief_content)
    return brief_path


def invoke_athena(brief_path):
    """Invoke Athena headlessly. Returns (success: bool, error: str or None)."""
    if not ATHENA_SKILL_PATH.exists():
        return False, "Athena skill not found at " + str(ATHENA_SKILL_PATH)

    # Load and extract Athena skill content (strip YAML frontmatter)
    athena_content = ATHENA_SKILL_PATH.read_text()
    if athena_content.startswith("---"):
        match = re.match(r"^---\n.*?\n---\n(.*)", athena_content, re.DOTALL)
        if match:
            athena_content = match.group(1).strip()

    prompt = f"""Run the Athena skill on this brief: {brief_path}

Process all six steps (Pallas research, Erichthonius estimate, Nike questions/proposal, gate prep) and save the complete Athena Report to context/pipeline/athena/."""

    result = subprocess.run(
        ["claude", "-p", prompt, "--system", athena_content, "--output-format", "text"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )

    if result.returncode != 0:
        return False, f"claude exited {result.returncode}: {result.stderr[:100]}"

    if not result.stdout.strip():
        return False, "athena produced no output"

    return True, None


def invoke_plutus(athena_report_path):
    """Invoke Plutus headlessly to add margin check to Athena report. Returns (success: bool, error: str or None)."""
    if not PLUTUS_SKILL_PATH.exists():
        return False, "Plutus skill not found at " + str(PLUTUS_SKILL_PATH)

    # Load and extract Plutus skill content (strip YAML frontmatter)
    plutus_content = PLUTUS_SKILL_PATH.read_text()
    if plutus_content.startswith("---"):
        match = re.match(r"^---\n.*?\n---\n(.*)", plutus_content, re.DOTALL)
        if match:
            plutus_content = match.group(1).strip()

    prompt = f"""Run the Plutus skill to review the Athena report and append a margin check.

Report path: {athena_report_path}

Process all five steps (load report, Poros margin check, Euporia tax adjustment, Penia viability, gate prep) and append the Financial Review section to the Athena report."""

    result = subprocess.run(
        ["claude", "-p", prompt, "--system", plutus_content, "--output-format", "text"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )

    if result.returncode != 0:
        return False, f"claude exited {result.returncode}: {result.stderr[:100]}"

    if not result.stdout.strip():
        return False, "plutus produced no output"

    return True, None


def find_pending():
    if not INBOX_DIR.exists():
        return []
    pending = []
    for path in sorted(INBOX_DIR.glob("*.md")):
        if "status: pending" in path.read_text():
            pending.append(path)
    return pending


def postman_sweep():
    """Dispatch any pending postman messages across all project inboxes."""
    try:
        import sys
        sys.path.insert(0, str(PROJECT_ROOT / 'studio'))
        from postman import sweep
        n = sweep()
        print(f"{LOG_PREFIX}: postman sweep — {n} message(s) dispatched")
    except Exception as e:
        print(f"{LOG_PREFIX}: postman sweep error — {e}", file=sys.stderr)


def main():
    pending = find_pending()

    if not pending:
        print(f"{LOG_PREFIX}: inbox empty, nothing to route")
        postman_sweep()
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

        # If verdict is Pursue, invoke Athena then Plutus
        if verdict == "Pursue":
            slug = create_brief_slug(meta)
            brief_path = create_brief_file(meta, body, slug)
            success, athena_error = invoke_athena(brief_path)
            if success:
                print(f"{LOG_PREFIX}:     ✓ Athena invoked (brief: {slug})")

                # Now invoke Plutus to add margin check
                today = datetime.datetime.now().strftime('%Y-%m-%d')
                athena_report_path = PROJECT_ROOT / "context" / "pipeline" / "athena" / f"{slug}-{today}.md"
                p_success, p_error = invoke_plutus(str(athena_report_path))
                if p_success:
                    print(f"{LOG_PREFIX}:     ✓ Plutus invoked (margin check added)")
                else:
                    print(f"{LOG_PREFIX}:     ✗ Plutus failed: {p_error}", file=sys.stderr)
            else:
                print(f"{LOG_PREFIX}:     ✗ Athena failed: {athena_error}", file=sys.stderr)

        ok += 1

    print(f"{LOG_PREFIX}: done — {ok} triaged, {skipped} skipped, {failed} failed — total ${total_cost:.3f}")
    postman_sweep()


if __name__ == "__main__":
    main()
