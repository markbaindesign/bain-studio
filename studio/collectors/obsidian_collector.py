#!/usr/bin/env python3
"""
Obsidian collector — harvests tagged ideas from daily notes.

Scans daily notes (YYYY-MM-DD.md) in the Obsidian vault for hashtag-prefixed lines.
Routes items to topic files in Ideas/ and drops spec stubs for #project and #skill.

Usage:
    python3 studio/collectors/obsidian_collector.py          # process new notes
    python3 studio/collectors/obsidian_collector.py --all    # reprocess all notes
    python3 studio/collectors/obsidian_collector.py --dry-run

Cron example (daily at 7am):
    0 7 * * * cd /media/data/dev/bain-studio && python3 studio/collectors/obsidian_collector.py >> studio/collectors/obsidian_collector.log 2>&1
"""

import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

import os
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# OBSIDIAN_VAULT: root of the vault (default ~/dropbox/Notes)
VAULT = Path(os.getenv("OBSIDIAN_VAULT", Path.home() / "dropbox/Notes"))
# OBSIDIAN_DAILY_SUBDIR: subfolder for daily notes within the vault, or "" for root
_daily_subdir = os.getenv("OBSIDIAN_DAILY_SUBDIR", "")
DAILY_DIR = VAULT / _daily_subdir if _daily_subdir else VAULT

CONTENT_DIR = Path(os.getenv("STUDIO_CONTENT_DIR", Path(__file__).parent.parent.parent / "context"))
IDEAS_DIR = VAULT / "Ideas"
STATE_FILE = Path(__file__).parent / "obsidian_collector_state.json"
SPEC_DRAFTS = CONTENT_DIR / "specs" / "drafts"
STANDUP_SUMMARY = Path(__file__).parent / "obsidian_standup.json"

LOG_PREFIX = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] obsidian"

# Tags that go to spec drafts (stub file created)
SPEC_TAGS = {"project", "skill", "script"}

# Tags that route to Ideas/{tag}.md
IDEA_TAGS = {"workflow", "biz-dev", "boilerplate", "jbp", "bff"}

# All other tags go to Ideas/misc.md


def log(msg):
    print(f"{LOG_PREFIX} {msg}", flush=True)


def file_hash(path):
    return hashlib.md5(path.read_bytes()).hexdigest()


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"processed": {}}  # {filename: md5_hash}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def daily_notes(directory):
    """Yield Path objects for YYYY-MM-DD.md files, sorted oldest first."""
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")
    return sorted(p for p in directory.iterdir() if p.is_file() and pattern.match(p.name))


def extract_tagged_items(text, source_date):
    """
    Return list of {tag, text, date} dicts.

    Recognises:
      #tag text on the rest of the line
      #tag\ntext on next line (bare tag followed by content)
    """
    items = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Inline: #tag some content here
        m = re.match(r"^#([\w-]+)\s+(.+)", line)
        if m:
            items.append({"tag": m.group(1).lower(), "text": m.group(2).strip(), "date": source_date})
            i += 1
            continue
        # Bare tag on its own line — grab following non-empty, non-tag lines as body
        m = re.match(r"^#([\w-]+)$", line)
        if m:
            tag = m.group(1).lower()
            body_lines = []
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if not next_line:
                    break
                if re.match(r"^#[\w-]+", next_line):
                    break
                body_lines.append(next_line)
                j += 1
            if body_lines:
                items.append({"tag": tag, "text": " ".join(body_lines), "date": source_date})
                i = j
                continue
        i += 1
    return items


def slug(text):
    """Turn arbitrary text into a filename-safe slug."""
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:60].strip("-")


def append_to_ideas(tag, item, dry_run):
    """Append item to Ideas/{tag}.md, creating the file if needed."""
    IDEAS_DIR.mkdir(exist_ok=True)
    dest = IDEAS_DIR / f"{tag}.md"
    entry = f"- {item['text']}  _(from {item['date']})_\n"

    # Deduplicate: skip if identical text already present
    if dest.exists() and item["text"] in dest.read_text():
        return False

    if dry_run:
        log(f"  [dry] → Ideas/{tag}.md: {item['text'][:60]}")
        return True

    with dest.open("a") as f:
        if not dest.exists() or dest.stat().st_size == 0:
            f.write(f"# {tag.replace('-', ' ').title()}\n\n")
        f.write(entry)
    return True


def create_spec_stub(tag, item, dry_run):
    """Create a minimal spec stub in context/specs/drafts/ if one doesn't exist."""
    SPEC_DRAFTS.mkdir(parents=True, exist_ok=True)
    filename = f"{tag}-{slug(item['text'])}.md"
    dest = SPEC_DRAFTS / filename

    if dest.exists():
        return False, filename

    stub = f"""# {item['text']}

_Source: Obsidian daily note {item['date']} — #{tag}_

## Problem

<!-- What pain does this solve? -->

## Rough scope

<!-- What would done look like? -->

## Notes

<!-- Any context from the source note -->
"""

    if dry_run:
        log(f"  [dry] → context/specs/drafts/{filename}")
        return True, filename

    dest.write_text(stub)
    return True, filename


def process_note(path, dry_run):
    date_str = path.stem  # YYYY-MM-DD
    text = path.read_text()
    items = extract_tagged_items(text, date_str)

    counts = {"spec_stubs": 0, "ideas": 0, "skipped": 0}
    stub_names = []

    for item in items:
        tag = item["tag"]
        if tag in SPEC_TAGS:
            created, stub_file = create_spec_stub(tag, item, dry_run)
            if created:
                counts["spec_stubs"] += 1
                stub_names.append(stub_file)
                log(f"  stub: [{tag}] {item['text'][:60]}")
            else:
                counts["skipped"] += 1
        else:
            dest_tag = tag if tag in IDEA_TAGS else "misc"
            created = append_to_ideas(dest_tag, item, dry_run)
            if created:
                counts["ideas"] += 1
                log(f"  idea: [{dest_tag}] {item['text'][:60]}")
            else:
                counts["skipped"] += 1

    return counts, stub_names


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Reprocess all notes, not just new ones")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    state = load_state()
    # Migrate old list-based state to hash-based
    if isinstance(state.get("processed"), list):
        state["processed"] = {name: "" for name in state["processed"]}
    processed_hashes = state["processed"]  # {filename: hash}

    notes = daily_notes(DAILY_DIR)
    if not args.all:
        notes = [n for n in notes if file_hash(n) != processed_hashes.get(n.name)]

    if not notes:
        log("no new or changed notes to process")
        return

    log(f"processing {len(notes)} note(s){' [dry run]' if args.dry_run else ''}")

    total = {"spec_stubs": 0, "ideas": 0, "skipped": 0}
    newly_processed = {}
    new_stub_names = []

    for note in notes:
        log(f"→ {note.name}")
        counts, stubs = process_note(note, args.dry_run)
        for k in total:
            total[k] += counts[k]
        newly_processed[note.name] = file_hash(note)
        new_stub_names.extend(stubs)

    log(f"done — {total['spec_stubs']} spec stubs, {total['ideas']} ideas filed, {total['skipped']} duplicates skipped")

    if not args.dry_run:
        processed_hashes.update(newly_processed)
        state["processed"] = processed_hashes
        save_state(state)
        summary = {
            "run_at": datetime.datetime.now().isoformat(),
            "notes_processed": len(newly_processed),
            "spec_stubs": total["spec_stubs"],
            "ideas": total["ideas"],
            "new_stub_names": new_stub_names,
        }
        STANDUP_SUMMARY.write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
