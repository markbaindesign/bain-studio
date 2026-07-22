#!/usr/bin/env python3
"""Pure logic extracted from the studio-looper skill (.claude/skills/studio-looper/SKILL.md).

The skill previously embedded this logic as inline Python heredocs, which meant it was
never unit-tested and could silently drift from what the SKILL.md doc described. This
module is the single source of truth; SKILL.md invokes it via the CLI at the bottom of
this file instead of re-embedding the logic.

Covers:
  - Step 1a concurrency guard (LIVE / STALE state-file classification)
  - Step 2 queue building (Priority sort, ## DONE exclusion)
  - Step 2 orphan recovery (In Progress tasks with no live session)
  - Deadline calculation (earlier of quota reset / --for duration)

See studio/tests/test_looper_logic.py for unit tests.
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from pathlib import Path

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
DEFAULT_INACTIVITY_MINUTES = 15


# ---------------------------------------------------------------------------
# State-file parsing
# ---------------------------------------------------------------------------

def parse_state_frontmatter(text: str) -> dict:
    """Parse the YAML-ish frontmatter of a studio-looper state file."""
    if text.count("---") < 2:
        return {}
    fm = text.split("---")[1]
    out = {}
    # [ \t]*, not \s* — \s matches newlines too, so on an empty value ("key:\n")
    # a greedy \s* swallows the line break and bleeds into the next key's value.
    for m in re.finditer(r"^(\w+):[ \t]*(.*)$", fm, re.MULTILINE):
        out[m.group(1)] = m.group(2).strip()
    return out


@dataclass
class ConcurrencyResult:
    status: str  # "LIVE" or "STALE"
    path: str
    deadline: str
    session: str
    current_task: str
    reason: str = ""  # "deadline" or "inactive-{N}m", only for STALE


def classify_concurrency(
    state_files: list[tuple[str, str, datetime.datetime]],
    target_prefix: str,
    now: datetime.datetime,
    inactivity_minutes: int = DEFAULT_INACTIVITY_MINUTES,
) -> list[ConcurrencyResult]:
    """Classify each state file as LIVE or STALE for the given target queue.

    state_files: list of (path, file_text, mtime) tuples — the caller reads these from
    disk so this function stays pure and testable.
    Files whose target_prefix doesn't match are silently skipped (different queue,
    no conflict).
    """
    results = []
    for path, text, mtime in state_files:
        fm = parse_state_frontmatter(text)
        file_target = fm.get("target_prefix") or "SL"
        if file_target != target_prefix:
            continue

        deadline_s = fm.get("deadline", "")
        session = fm.get("session_id", "")
        current_task = fm.get("current_task", "")

        deadline = None
        if deadline_s:
            try:
                deadline = datetime.datetime.fromisoformat(deadline_s)
            except ValueError:
                pass

        idle_minutes = (now - mtime).total_seconds() / 60

        if deadline and now >= deadline:
            results.append(ConcurrencyResult("STALE", path, deadline_s, session, current_task, "deadline"))
        elif idle_minutes >= inactivity_minutes:
            results.append(ConcurrencyResult(
                "STALE", path, deadline_s, session, current_task, f"inactive-{idle_minutes:.0f}m"
            ))
        else:
            results.append(ConcurrencyResult("LIVE", path, deadline_s, session, current_task))
    return results


def classify_single_file(path: str, text: str, mtime: datetime.datetime, now: datetime.datetime,
                          inactivity_minutes: int = DEFAULT_INACTIVITY_MINUTES) -> ConcurrencyResult:
    """Classify one state file against its OWN target_prefix (read from its own
    frontmatter) — used by the PreToolUse hook to mechanically verify a specific file's
    LIVE/STALE status before allowing it to be deleted, independent of whatever an agent
    claims about it."""
    fm = parse_state_frontmatter(text)
    target_prefix = fm.get("target_prefix") or "SL"
    results = classify_concurrency([(path, text, mtime)], target_prefix, now, inactivity_minutes)
    return results[0]


# ---------------------------------------------------------------------------
# Mirror parsing / queue building
# ---------------------------------------------------------------------------

@dataclass
class MirrorTask:
    local_id: str
    title: str
    priority: str  # "High", "Medium", "Low", "none", or whatever the mirror has
    looper_status: str
    order: int  # position in the mirror, for stable tiebreak
    in_done_section: bool = False


_TASK_HEADER_RE = re.compile(r"^###\s*(.+)$", re.MULTILINE)


def parse_mirror_tasks(mirror_text: str) -> list[MirrorTask]:
    """Split a mirror file into task blocks, tagging each with its ## DONE membership."""
    done_idx = mirror_text.find("\n## DONE")
    blocks = re.split(r"\n(?=### )", mirror_text)

    tasks = []
    offset = 0
    for order, block in enumerate(blocks):
        block_start = mirror_text.find(block, offset)
        offset = block_start + 1 if block_start >= 0 else offset
        if not block.strip().startswith("###"):
            continue
        m = _TASK_HEADER_RE.match(block.strip())
        if not m:
            continue
        header_line = m.group(1).strip()
        local_id_m = re.search(r"\*\*Local ID:\*\*\s*(\S+)", block)
        local_id = local_id_m.group(1) if local_id_m else header_line.split()[0]
        prio_m = re.search(r"\*\*Priority:\*\*\s*(.+)", block)
        priority = prio_m.group(1).strip() if prio_m else "none"
        status_m = re.search(r"\*\*Looper Status:\*\*\s*(.+)", block)
        looper_status = status_m.group(1).strip() if status_m else ""
        in_done = done_idx != -1 and block_start > done_idx

        tasks.append(MirrorTask(
            local_id=local_id, title=header_line, priority=priority,
            looper_status=looper_status, order=order, in_done_section=in_done,
        ))
    return tasks


def build_queue(tasks: list[MirrorTask]) -> list[MirrorTask]:
    """Filter to workable Queue tasks and sort by Priority (High > Medium > Low > none),
    mirror order as tiebreak. Tasks in ## DONE are never queued regardless of status text
    (a completed task's stale 'Queue' field is noise, not work)."""
    workable = [
        t for t in tasks
        if not t.in_done_section and t.looper_status.strip().lower().startswith("queue")
    ]
    return sorted(workable, key=lambda t: (PRIORITY_ORDER.get(t.priority.strip().lower(), 3), t.order))


def find_orphans(tasks: list[MirrorTask], live_current_tasks: set[str]) -> list[str]:
    """Local IDs of tasks stuck at 'In progress' with no live session claiming them."""
    return [
        t.local_id for t in tasks
        if not t.in_done_section
        and t.looper_status.strip().lower() == "in progress"
        and t.local_id not in live_current_tasks
    ]


# ---------------------------------------------------------------------------
# Deadline calculation
# ---------------------------------------------------------------------------

def compute_deadline(
    reset_ts: float | None,
    for_deadline: datetime.datetime | None,
) -> datetime.datetime | None:
    """Earlier of the quota-reset time and a --for duration deadline. Either may be absent."""
    candidates = []
    if reset_ts:
        candidates.append(datetime.datetime.fromtimestamp(reset_ts))
    if for_deadline:
        candidates.append(for_deadline)
    return min(candidates) if candidates else None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli_concurrency(target_prefix: str, state_dir: str = "/tmp/studio-looper") -> None:
    now = datetime.datetime.now()
    state_files = []
    for p in sorted(Path(state_dir).glob("studio-looper.*.local.md")):
        try:
            text = p.read_text()
            mtime = datetime.datetime.fromtimestamp(p.stat().st_mtime)
            state_files.append((str(p), text, mtime))
        except OSError:
            continue

    for r in classify_concurrency(state_files, target_prefix, now):
        if r.status == "STALE":
            print(f"STALE:{r.path}:{r.deadline}:{r.session}:{r.current_task}:{r.reason}")
        else:
            print(f"LIVE:{r.path}:{r.deadline}:{r.session}:{r.current_task}")


def _cli_check_path(path: str) -> None:
    """Print LIVE, STALE, or MISSING for a single state file — used by the
    PreToolUse concurrency-guard hook (.claude/hooks/looper-concurrency-guard.sh) to
    mechanically verify a file before allowing it to be deleted."""
    p = Path(path)
    if not p.exists():
        print("MISSING")
        return
    now = datetime.datetime.now()
    text = p.read_text()
    mtime = datetime.datetime.fromtimestamp(p.stat().st_mtime)
    print(classify_single_file(str(p), text, mtime, now).status)


def _cli_queue(mirror_path: str) -> None:
    text = Path(mirror_path).read_text()
    tasks = parse_mirror_tasks(text)
    for t in build_queue(tasks):
        print(f"{t.local_id}\t{t.priority}\t{t.title}")


def _cli_orphans(mirror_path: str, live_tasks: str) -> None:
    text = Path(mirror_path).read_text()
    tasks = parse_mirror_tasks(text)
    live = set(filter(None, live_tasks.split(",")))
    for local_id in find_orphans(tasks, live):
        print(local_id)


def _cli_deadline(reset_ts: str, for_deadline: str) -> None:
    rt = float(reset_ts) if reset_ts else None
    fd = datetime.datetime.fromisoformat(for_deadline) if for_deadline else None
    result = compute_deadline(rt, fd)
    print(result.isoformat() if result else "")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("usage: looper_logic.py {concurrency|queue|orphans|deadline|check-path} ...", file=sys.stderr)
        sys.exit(2)

    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "concurrency":
        _cli_concurrency(*args)
    elif cmd == "queue":
        _cli_queue(*args)
    elif cmd == "orphans":
        _cli_orphans(*args)
    elif cmd == "check-path":
        _cli_check_path(*args)
    elif cmd == "deadline":
        _cli_deadline(*args)
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        sys.exit(2)
