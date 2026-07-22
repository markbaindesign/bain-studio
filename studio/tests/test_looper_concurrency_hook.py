"""Tests for .claude/hooks/looper-concurrency-guard.sh — the mechanical, hook-based
enforcement of the studio-looper concurrency guard.

An eval (test_looper_evals.py::test_concurrency_live_blocks_second_run) caught the
headless agent, running on --model haiku, misclassifying a genuinely LIVE conflict as
stale and clearing it anyway (2026-07-22). Prose guard rails in SKILL.md aren't
enforcement — this hook independently re-runs the exact tested classification logic
(studio/scripts/looper_logic.py) and denies the tool call outright when it disagrees
with what the agent is about to do, regardless of the agent's own reasoning.

These tests invoke the hook script directly with crafted PreToolUse-shaped JSON on
stdin — deterministic and free, no live claude invocation needed.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).parent.parent.parent / ".claude" / "hooks" / "looper-concurrency-guard.sh"
STATE_DIR = Path("/tmp/studio-looper")


def run_hook(tool_input: dict) -> tuple[int, dict | None]:
    payload = json.dumps({"tool_input": tool_input})
    r = subprocess.run(["bash", str(HOOK)], input=payload, capture_output=True, text=True, timeout=10)
    out = r.stdout.strip()
    return r.returncode, (json.loads(out) if out else None)


@pytest.fixture(autouse=True)
def clean_state_dir():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    before = set(STATE_DIR.glob("studio-looper.hooktest-*.local.md"))
    yield
    for p in STATE_DIR.glob("studio-looper.hooktest-*.local.md"):
        if p not in before:
            p.unlink(missing_ok=True)


def write_fixture(session_id: str, deadline: str, target_prefix: str = "SLT", mtime_offset_min: int = 0) -> Path:
    p = STATE_DIR / f"studio-looper.{session_id}.local.md"
    p.write_text(f"""---
session_id: {session_id}
current_task: SLT-001
deadline: {deadline}
target_prefix: {target_prefix}
---
""")
    if mtime_offset_min:
        import os
        import time
        ts = time.time() - mtime_offset_min * 60
        os.utime(p, (ts, ts))
    return p


def test_write_denied_when_another_session_is_live():
    write_fixture("hooktest-existing-live", "2099-01-01T00:00:00")
    code, decision = run_hook({
        "file_path": str(STATE_DIR / "studio-looper.hooktest-new.local.md"),
        "content": "---\nsession_id: hooktest-new\ncurrent_task: SLT-002\ndeadline: 2099-01-01T00:00:00\ntarget_prefix: SLT\n---\n",
    })
    assert code == 0
    assert decision is not None
    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "hooktest-existing-live" in decision["hookSpecificOutput"]["permissionDecisionReason"]


def test_write_allowed_when_no_conflict():
    code, decision = run_hook({
        "file_path": str(STATE_DIR / "studio-looper.hooktest-new.local.md"),
        "content": "---\nsession_id: hooktest-new\ncurrent_task: SLT-002\ndeadline: 2099-01-01T00:00:00\ntarget_prefix: SLT\n---\n",
    })
    assert code == 0
    assert decision is None


def test_write_denied_ignores_different_target_prefix():
    write_fixture("hooktest-existing-live-sl", "2099-01-01T00:00:00", target_prefix="SL")
    code, decision = run_hook({
        "file_path": str(STATE_DIR / "studio-looper.hooktest-new.local.md"),
        "content": "---\nsession_id: hooktest-new\ncurrent_task: SLT-002\ndeadline: 2099-01-01T00:00:00\ntarget_prefix: SLT\n---\n",
    })
    assert code == 0
    assert decision is None


def test_rm_denied_on_live_file():
    fixture = write_fixture("hooktest-rm-live", "2099-01-01T00:00:00")
    code, decision = run_hook({"command": f"rm -f {fixture}"})
    assert code == 0
    assert decision is not None
    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert fixture.exists()  # the hook doesn't delete anything itself — it just denies


def test_rm_allowed_on_stale_file():
    fixture = write_fixture("hooktest-rm-stale", "2020-01-01T00:00:00", mtime_offset_min=30)
    code, decision = run_hook({"command": f"rm -f {fixture}"})
    assert code == 0
    assert decision is None
    fixture.unlink(missing_ok=True)


def test_unrelated_bash_command_passes_through():
    code, decision = run_hook({"command": "git status"})
    assert code == 0
    assert decision is None


def test_unrelated_write_passes_through():
    code, decision = run_hook({"file_path": "/tmp/some-other-file.txt", "content": "hello"})
    assert code == 0
    assert decision is None
