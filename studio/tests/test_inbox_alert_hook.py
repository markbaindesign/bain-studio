"""Tests for .claude/hooks/inbox-alert.py, which puts unread postman mail in Claude's context."""

import json
import os
import subprocess
from pathlib import Path

HOOK = Path(__file__).parent.parent.parent / ".claude" / "hooks" / "inbox-alert.py"


def run_hook(cwd, event="UserPromptSubmit"):
    env = {k: v for k, v in os.environ.items() if k != "TMUX_PANE"}
    r = subprocess.run(["python3", str(HOOK)], input=json.dumps({"hook_event_name": event, "cwd": str(cwd)}),
                       capture_output=True, text=True, timeout=10, env=env)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout) if r.stdout.strip() else None


def _inbox(root):
    inbox = root / ".claude" / "inbox"
    inbox.mkdir(parents=True)
    return inbox


def test_unread_mail_is_added_to_context_from_a_subdirectory(tmp_path):
    inbox = _inbox(tmp_path)
    (inbox / "msg-1.md").write_text("---\nfrom: claude-kf\nsubject: Deploy question\npriority: high\n---\n\nBody\n")
    (tmp_path / "src").mkdir()
    out = run_hook(tmp_path / "src")
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert out["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "[high] Deploy question (from claude-kf" in ctx
    assert "/check-inbox" in ctx


def test_studio_inbox_counts_too(tmp_path):
    _inbox(tmp_path)
    studio_inbox = tmp_path / "studio" / "inbox"
    studio_inbox.mkdir(parents=True)
    (studio_inbox / "msg-2.md").write_text("---\nsubject: For the studio\n---\n")
    assert "For the studio" in run_hook(tmp_path, "SessionStart")["hookSpecificOutput"]["additionalContext"]


def test_silent_when_inbox_empty_or_only_processed(tmp_path):
    inbox = _inbox(tmp_path)
    (inbox / "processed").mkdir()
    (inbox / "processed" / "msg-1.md").write_text("---\nsubject: old\n---\n")
    assert run_hook(tmp_path) is None


def test_stop_event_never_injects(tmp_path):
    (_inbox(tmp_path) / "msg-1.md").write_text("---\nsubject: x\n---\n")
    assert run_hook(tmp_path, "Stop") is None
