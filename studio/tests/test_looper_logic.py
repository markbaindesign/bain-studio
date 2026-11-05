import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from looper_logic import (
    WINDOW_EXIT_DEADLINE,
    WINDOW_EXIT_MAX_ITERATIONS,
    WINDOW_EXIT_NO_PROGRESS,
    _cli_concurrency,
    _cli_live_tasks,
    classify_concurrency,
    classify_single_file,
    build_queue,
    compute_deadline,
    find_orphans,
    parse_mirror_tasks,
    parse_state_frontmatter,
    window_summary,
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


# ---------------------------------------------------------------------------
# _cli_concurrency output contract
#
# The CLEAR line exists because silence is a weak signal. On 2026-11-05 a
# headless run read empty output as "the guard is broken", went looking at
# processes, found the runner's own lock and its own `claude -p` child, and
# refused to start — ending the nightly window after 1 of 6 tasks.
# ---------------------------------------------------------------------------

def test_cli_concurrency_prints_clear_when_no_state_files(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("LOOPER_RUN_ID", raising=False)
    _cli_concurrency("SL", str(tmp_path))
    assert capsys.readouterr().out.strip() == "CLEAR:no other session targets SL"


def test_cli_concurrency_clear_names_runner_when_launched_by_it(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("LOOPER_RUN_ID", "20261105-0200")
    _cli_concurrency("SL", str(tmp_path))
    out = capsys.readouterr().out.strip()
    assert out.startswith("CLEAR:no other session targets SL")
    assert "launched by runner 20261105-0200" in out


def test_cli_concurrency_no_clear_line_when_a_run_is_live(tmp_path, capsys, monkeypatch):
    """CLEAR must never co-exist with LIVE — that would be contradictory output."""
    monkeypatch.delenv("LOOPER_RUN_ID", raising=False)
    state = tmp_path / "studio-looper.sess-live.local.md"
    state.write_text(_state_text("sess-live", "SL-001", "2099-01-01T00:00:00"))
    _cli_concurrency("SL", str(tmp_path))
    out = capsys.readouterr().out
    assert "LIVE:" in out
    assert "CLEAR:" not in out


def test_cli_concurrency_ignores_other_queues_and_still_reports_clear(tmp_path, capsys, monkeypatch):
    """A live SLT sandbox run is not a conflict for SL — SL must still read CLEAR."""
    monkeypatch.delenv("LOOPER_RUN_ID", raising=False)
    state = tmp_path / "studio-looper.sess-slt.local.md"
    state.write_text(_state_text("sess-slt", "SLT-001", "2099-01-01T00:00:00", target_prefix="SLT"))
    _cli_concurrency("SL", str(tmp_path))
    assert capsys.readouterr().out.strip() == "CLEAR:no other session targets SL"


# ---------------------------------------------------------------------------
# window_summary
#
# The runner infers progress from task-looper.log growing, so a session that
# declines to start looks exactly like a drained queue. Only no-progress with
# work still queued is anomalous; the deadline and iteration-cap exits are
# ordinary and must not be reported as a refusal.
# ---------------------------------------------------------------------------

def test_window_summary_drained_queue_is_normal():
    log_line, msg, priority = window_summary("immediate", 6, [], WINDOW_EXIT_NO_PROGRESS)
    assert priority == "normal"
    assert "queue drained" in log_line
    assert "queue drained" in msg
    assert "ended early" not in msg


def test_window_summary_drained_but_nothing_done_is_high():
    """Zero productive iterations and an empty queue still warrants a look."""
    _, _, priority = window_summary("immediate", 0, [], WINDOW_EXIT_NO_PROGRESS)
    assert priority == "high"


def test_window_summary_no_progress_with_work_left_flags_early_stop():
    """The 2026-11-05 case: 1 of 6 done, iteration 2 refused, window closed."""
    log_line, msg, priority = window_summary(
        "immediate", 1, ["BD-190", "BD-192", "BD-183", "BD-185", "BD-172"],
        WINDOW_EXIT_NO_PROGRESS,
    )
    assert priority == "high"
    assert "ENDED EARLY" in log_line
    assert "5 task(s) still queued" in msg
    assert "BD-190" in msg and "BD-172" in msg
    assert "refused to start" in msg


def test_window_summary_deadline_with_work_left_is_not_an_early_stop():
    """Hitting the quota deadline with work queued is ordinary — don't cry refusal."""
    log_line, msg, priority = window_summary(
        "immediate", 12, ["BD-190", "BD-192"], WINDOW_EXIT_DEADLINE
    )
    assert priority == "normal"
    assert "ENDED EARLY" not in log_line
    assert "deadline" in log_line
    assert "carry over" in msg
    assert "refused to start" not in msg


def test_window_summary_iteration_cap_with_work_left_is_not_an_early_stop():
    log_line, msg, priority = window_summary(
        "immediate", 30, ["BD-190"], WINDOW_EXIT_MAX_ITERATIONS
    )
    assert priority == "normal"
    assert "cap" in log_line
    assert "refused to start" not in msg
    # tasks_done is PRODUCTIVE iterations, never the cap value — "hit the
    # 30-iteration cap" would be a lie whenever some iteration made no progress.
    assert "30-iteration cap" not in msg
    assert "after 30 productive iteration(s)" in msg


def test_window_summary_truncates_a_long_remaining_list():
    remaining = [f"BD-{n}" for n in range(100, 110)]
    log_line, msg, _ = window_summary("immediate", 1, remaining, WINDOW_EXIT_NO_PROGRESS)
    assert "10 task(s) still queued" in msg
    assert "…" in log_line
    assert "BD-109" not in msg


# ---------------------------------------------------------------------------
# _cli_live_tasks
#
# Replaces SKILL.md Step 2's `concurrency | grep '^LIVE:' | cut -d: -f5`. The
# deadline is an ISO timestamp, so its colons shifted every later field and -f5
# returned "00" instead of the task ID — orphan recovery's live set was always
# wrong, and could reset an in-flight task back to Queue.
# ---------------------------------------------------------------------------

def test_cli_live_tasks_prints_current_task_not_a_timestamp_fragment(tmp_path, capsys):
    state = tmp_path / "studio-looper.sess-x.local.md"
    state.write_text(_state_text("sess-x", "SL-042", "2099-01-01T20:00:00"))
    _cli_live_tasks("SL", str(tmp_path))
    assert capsys.readouterr().out.split() == ["SL-042"]


def test_cli_live_tasks_excludes_stale_sessions(tmp_path, capsys):
    """A stale file's task is an orphan candidate, so it must not count as live."""
    stale = tmp_path / "studio-looper.sess-old.local.md"
    stale.write_text(_state_text("sess-old", "SL-099", "2000-01-01T00:00:00"))
    _cli_live_tasks("SL", str(tmp_path))
    assert capsys.readouterr().out.strip() == ""


def test_cli_live_tasks_excludes_other_queues(tmp_path, capsys):
    state = tmp_path / "studio-looper.sess-slt.local.md"
    state.write_text(_state_text("sess-slt", "SLT-001", "2099-01-01T20:00:00", target_prefix="SLT"))
    _cli_live_tasks("SL", str(tmp_path))
    assert capsys.readouterr().out.strip() == ""


def test_cli_live_tasks_lists_every_live_session_one_per_line(tmp_path, capsys):
    for sess, task in (("a", "SL-001"), ("b", "SL-002")):
        (tmp_path / f"studio-looper.sess-{sess}.local.md").write_text(
            _state_text(f"sess-{sess}", task, "2099-01-01T20:00:00")
        )
    _cli_live_tasks("SL", str(tmp_path))
    assert sorted(capsys.readouterr().out.split()) == ["SL-001", "SL-002"]
