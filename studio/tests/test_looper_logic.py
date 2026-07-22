import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from looper_logic import (
    classify_concurrency,
    classify_single_file,
    build_queue,
    compute_deadline,
    find_orphans,
    parse_mirror_tasks,
    parse_state_frontmatter,
)


# ---------------------------------------------------------------------------
# parse_state_frontmatter
# ---------------------------------------------------------------------------

def test_parse_state_frontmatter_basic():
    text = """---
session_id: abc123
current_task: SL-001
deadline: 2026-07-22T15:00:00
target_prefix: SL
---
SL-002
SL-003
"""
    fm = parse_state_frontmatter(text)
    assert fm["session_id"] == "abc123"
    assert fm["current_task"] == "SL-001"
    assert fm["target_prefix"] == "SL"


def test_parse_state_frontmatter_no_fences_returns_empty():
    assert parse_state_frontmatter("just some text, no frontmatter") == {}


def test_parse_state_frontmatter_blank_value_does_not_swallow_next_key():
    # Regression: a bare `\s*` separator matches newlines too, so a blank value
    # ("stop_at_pct:" with nothing after it — the normal case when --use isn't
    # passed) greedily consumed the line break and the next key/value ended up
    # captured as this key's value. Real production state files hit this on
    # every run without --use, silently breaking target_prefix (and therefore
    # the whole concurrency guard).
    text = """---
session_id: abc123
current_task: SL-001
deadline: 2026-07-22T15:00:00
stop_at_pct:
target_prefix: SL
---
"""
    fm = parse_state_frontmatter(text)
    assert fm["stop_at_pct"] == ""
    assert fm["target_prefix"] == "SL"


# ---------------------------------------------------------------------------
# classify_concurrency
# ---------------------------------------------------------------------------

def _state_text(session_id, current_task, deadline, target_prefix="SL"):
    return f"""---
session_id: {session_id}
current_task: {current_task}
deadline: {deadline}
target_prefix: {target_prefix}
---
"""


def test_concurrency_live_when_deadline_future_and_recently_touched():
    now = datetime.datetime(2026, 7, 22, 14, 0, 0)
    future_deadline = "2026-07-22T15:00:00"
    text = _state_text("sess-a", "SL-001", future_deadline)
    state_files = [("/tmp/x.md", text, now - datetime.timedelta(minutes=2))]

    results = classify_concurrency(state_files, "SL", now)
    assert len(results) == 1
    assert results[0].status == "LIVE"
    assert results[0].session == "sess-a"
    assert results[0].current_task == "SL-001"


def test_concurrency_stale_when_deadline_passed():
    now = datetime.datetime(2026, 7, 22, 15, 5, 0)
    past_deadline = "2026-07-22T15:00:00"
    text = _state_text("sess-b", "SL-002", past_deadline)
    state_files = [("/tmp/y.md", text, now - datetime.timedelta(minutes=1))]

    results = classify_concurrency(state_files, "SL", now)
    assert results[0].status == "STALE"
    assert results[0].reason == "deadline"


def test_concurrency_stale_when_inactive_even_if_deadline_future():
    now = datetime.datetime(2026, 7, 22, 14, 0, 0)
    future_deadline = "2026-07-22T20:00:00"
    text = _state_text("sess-c", "SL-003", future_deadline)
    state_files = [("/tmp/z.md", text, now - datetime.timedelta(minutes=20))]

    results = classify_concurrency(state_files, "SL", now)
    assert results[0].status == "STALE"
    assert "inactive-20m" in results[0].reason


def test_concurrency_ignores_different_target_prefix():
    now = datetime.datetime(2026, 7, 22, 14, 0, 0)
    text = _state_text("sess-d", "SLT-001", "2026-07-22T20:00:00", target_prefix="SLT")
    state_files = [("/tmp/w.md", text, now)]

    results = classify_concurrency(state_files, "SL", now)
    assert results == []


def test_concurrency_no_state_files_no_conflict():
    now = datetime.datetime(2026, 7, 22, 14, 0, 0)
    assert classify_concurrency([], "SL", now) == []


def test_concurrency_defaults_target_prefix_to_SL_when_absent():
    now = datetime.datetime(2026, 7, 22, 14, 0, 0)
    text = """---
session_id: sess-e
current_task: SL-005
deadline: 2026-07-22T20:00:00
---
"""
    state_files = [("/tmp/v.md", text, now)]
    results = classify_concurrency(state_files, "SL", now)
    assert len(results) == 1
    assert results[0].status == "LIVE"


# ---------------------------------------------------------------------------
# parse_mirror_tasks / build_queue
# ---------------------------------------------------------------------------

MIRROR = """\
# Bot Asana Task Mirror
Last synced: 2026-07-22

## Studio Looper

### SL-001 — Low priority task
- **Local ID:** SL-001
- **Priority:** Low
- **Looper Status:** Queue

### SL-002 — High priority task
- **Local ID:** SL-002
- **Priority:** High
- **Looper Status:** Queue

### SL-003 — Medium priority task, blocked
- **Local ID:** SL-003
- **Priority:** Medium
- **Looper Status:** Blocked

### SL-004 — No priority task
- **Local ID:** SL-004
- **Priority:** none
- **Looper Status:** Queue

### SL-005 — Another high priority task
- **Local ID:** SL-005
- **Priority:** High
- **Looper Status:** Queue

## DONE

### SL-099 — Completed task with stale Queue status
- **Local ID:** SL-099
- **Priority:** High
- **Looper Status:** Queue (completed, not workable)
"""


def test_parse_mirror_tasks_extracts_all_tasks_and_done_flag():
    tasks = parse_mirror_tasks(MIRROR)
    ids = [t.local_id for t in tasks]
    assert ids == ["SL-001", "SL-002", "SL-003", "SL-004", "SL-005", "SL-099"]
    done_flags = {t.local_id: t.in_done_section for t in tasks}
    assert done_flags["SL-005"] is False
    assert done_flags["SL-099"] is True


def test_build_queue_orders_by_priority_then_mirror_order():
    tasks = parse_mirror_tasks(MIRROR)
    queue = build_queue(tasks)
    # High (SL-002, SL-005, mirror order) > Low (SL-001) > none (SL-004); SL-003 excluded (Blocked)
    assert [t.local_id for t in queue] == ["SL-002", "SL-005", "SL-001", "SL-004"]


def test_build_queue_excludes_blocked_and_done_section():
    tasks = parse_mirror_tasks(MIRROR)
    queue_ids = {t.local_id for t in build_queue(tasks)}
    assert "SL-003" not in queue_ids  # Blocked, not Queue
    assert "SL-099" not in queue_ids  # in DONE despite "Queue" text
    assert "SL-001" in queue_ids


def test_build_queue_low_priority_sorts_after_none_is_false():
    tasks = parse_mirror_tasks(MIRROR)
    queue = build_queue(tasks)
    prios = [t.priority.lower() for t in queue]
    # Low priority task IS queued too, just sorts after high, before none.
    assert "low" in [t.priority.lower() for t in tasks if t.local_id == "SL-001"]
    # SL-001 is Low and Queue - should be in queue at all
    ids = [t.local_id for t in queue]
    assert "SL-001" in ids
    assert ids.index("SL-001") > ids.index("SL-002")  # Low sorts after High
    assert ids.index("SL-004") > ids.index("SL-001")   # none sorts after Low


# ---------------------------------------------------------------------------
# find_orphans
# ---------------------------------------------------------------------------

ORPHAN_MIRROR = """\
# Bot Asana Task Mirror

## Studio Looper

### SL-010 — Stuck in progress, no live session
- **Local ID:** SL-010
- **Priority:** High
- **Looper Status:** In progress

### SL-011 — In progress, claimed by a live session
- **Local ID:** SL-011
- **Priority:** High
- **Looper Status:** In progress

### SL-012 — Just queued, not an orphan
- **Local ID:** SL-012
- **Priority:** High
- **Looper Status:** Queue

## DONE

### SL-013 — Done section, stale in-progress text
- **Local ID:** SL-013
- **Priority:** High
- **Looper Status:** In progress
"""


def test_find_orphans_flags_unclaimed_in_progress_only():
    tasks = parse_mirror_tasks(ORPHAN_MIRROR)
    orphans = find_orphans(tasks, live_current_tasks={"SL-011"})
    assert orphans == ["SL-010"]


def test_find_orphans_ignores_done_section():
    tasks = parse_mirror_tasks(ORPHAN_MIRROR)
    orphans = find_orphans(tasks, live_current_tasks=set())
    assert "SL-013" not in orphans


def test_find_orphans_empty_when_all_claimed():
    tasks = parse_mirror_tasks(ORPHAN_MIRROR)
    orphans = find_orphans(tasks, live_current_tasks={"SL-010", "SL-011"})
    assert orphans == []


# ---------------------------------------------------------------------------
# compute_deadline
# ---------------------------------------------------------------------------

def test_compute_deadline_picks_earlier_of_reset_and_for():
    reset_ts = datetime.datetime(2026, 7, 22, 15, 20, 0).timestamp()
    for_deadline = datetime.datetime(2026, 7, 22, 15, 0, 0)
    result = compute_deadline(reset_ts, for_deadline)
    assert result == for_deadline


def test_compute_deadline_picks_reset_when_earlier():
    reset_ts = datetime.datetime(2026, 7, 22, 14, 30, 0).timestamp()
    for_deadline = datetime.datetime(2026, 7, 22, 15, 0, 0)
    result = compute_deadline(reset_ts, for_deadline)
    assert result == datetime.datetime.fromtimestamp(reset_ts)


def test_compute_deadline_handles_only_reset():
    reset_ts = datetime.datetime(2026, 7, 22, 14, 30, 0).timestamp()
    result = compute_deadline(reset_ts, None)
    assert result == datetime.datetime.fromtimestamp(reset_ts)


def test_compute_deadline_handles_only_for():
    for_deadline = datetime.datetime(2026, 7, 22, 15, 0, 0)
    result = compute_deadline(None, for_deadline)
    assert result == for_deadline


def test_compute_deadline_none_when_neither_set():
    assert compute_deadline(None, None) is None


# ---------------------------------------------------------------------------
# classify_single_file — used by the PreToolUse hook to mechanically verify a
# specific file's status before allowing an agent to delete it (see
# .claude/hooks/looper-concurrency-guard.sh)
# ---------------------------------------------------------------------------

def test_classify_single_file_live():
    now = datetime.datetime(2026, 7, 22, 14, 0, 0)
    text = _state_text("sess-hook-1", "SLT-001", "2026-07-22T20:00:00", target_prefix="SLT")
    result = classify_single_file("/tmp/f.md", text, now, now)
    assert result.status == "LIVE"


def test_classify_single_file_stale_by_deadline():
    now = datetime.datetime(2026, 7, 22, 15, 5, 0)
    text = _state_text("sess-hook-2", "SLT-001", "2026-07-22T15:00:00", target_prefix="SLT")
    result = classify_single_file("/tmp/f.md", text, now, now)
    assert result.status == "STALE"
    assert result.reason == "deadline"


def test_classify_single_file_stale_by_inactivity():
    now = datetime.datetime(2026, 7, 22, 14, 0, 0)
    mtime = now - datetime.timedelta(minutes=20)
    text = _state_text("sess-hook-3", "SLT-001", "2026-07-22T20:00:00", target_prefix="SLT")
    result = classify_single_file("/tmp/f.md", text, mtime, now)
    assert result.status == "STALE"
    assert "inactive-20m" in result.reason
