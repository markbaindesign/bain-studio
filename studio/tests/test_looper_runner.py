"""The looper works each task in a worktree of its own, never in the project's checkout.

BSTD-893. Real git in a temp repo; `claude` is a fake script, so no tokens and no
Asana: the runner's Asana side (set_status, post_note, notify) is stubbed.
"""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import bot_worktree  # noqa: E402
from looper_logic import (  # noqa: E402
    MirrorTask,
    looper_names,
    parse_mirror_tasks,
    parse_outcome,
    set_task_fields,
)

MIRROR = """# Studio Looper

## QUEUED

### BD-7 — Fix the header
- **Local ID:** BD-7
- **Asana ID:** 1001
- **Looper Status:** Queue
- **Assignee:** DevBot (9)
- **Notes:** mentions BD-8 on purpose

### BD-8 — Fix the footer
- **Local ID:** BD-8
- **Asana ID:** 1002
- **Looper Status:** Queue
- **Assignee:** DevBot (9)
"""


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def test_mirror_tasks_carry_their_asana_id():
    assert [t.asana_id for t in parse_mirror_tasks(MIRROR)] == ["1001", "1002"]


def test_set_task_fields_touches_only_the_named_task():
    out = set_task_fields(MIRROR, "BD-8", {"Looper Status": "Review", "Assignee": "Mark (2)"})
    t7, t8 = parse_mirror_tasks(out)
    assert t7.looper_status == "Queue" and t8.looper_status == "Review"
    assert "- **Assignee:** Mark (2)" in out and out.count("DevBot (9)") == 1


def test_set_task_fields_refuses_a_missing_task_or_line():
    with pytest.raises(KeyError):
        set_task_fields(MIRROR, "BD-99", {"Looper Status": "Review"})
    with pytest.raises(KeyError):
        set_task_fields(MIRROR, "BD-7", {"Blockers": "x"})


def test_parse_outcome_takes_the_last_promise_for_this_task_only():
    assert parse_outcome("x <promise>BD-7_BLOCKED</promise> <promise>BD-7_COMPLETE</promise>",
                         "BD-7") == "COMPLETE"
    assert parse_outcome("<promise>BD-8_COMPLETE</promise>", "BD-7") == ""
    assert parse_outcome("", "BD-7") == ""


def test_looper_names_give_each_task_its_own_branch():
    assert looper_names("20261119-0200", "KF-WEB-12") == (
        "looper-20261119-0200-KF-WEB-12", "looper/20261119-0200/KF-WEB-12")


# ---------------------------------------------------------------------------
# The run itself: temp repo, fake claude
# ---------------------------------------------------------------------------

FAKE_CLAUDE = """#!/bin/sh
# Stands in for `claude -p`: records its argv, maybe commits, prints a promise.
printf '%s\\n' "$@" > "$FAKE_ARGV"
if [ "$FAKE_WORK" = "commit" ]; then
  echo work > work.txt && git add work.txt && git commit -qm "work ($FAKE_LID)"
fi
[ -n "$FAKE_OUTCOME" ] && echo "<promise>${FAKE_LID}_${FAKE_OUTCOME}</promise>"
exit 0
"""


@pytest.fixture
def env(tmp_path, monkeypatch):
    import looper_runner as lr

    root = tmp_path / "proj"
    root.mkdir()
    for k, v in {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
                 "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}.items():
        monkeypatch.setenv(k, v)
    git = lambda *a, cwd=root: subprocess.run(["git", *a], cwd=cwd, check=True,
                                              capture_output=True, text=True).stdout
    git("init", "-q")
    git("checkout", "-q", "-b", "develop")
    (root / "f.txt").write_text("x")
    git("add", ".")
    git("commit", "-qm", "init")
    # Mark is mid-edit in his checkout: a staged change and an untracked file.
    (root / "f.txt").write_text("marks wip")
    git("add", "f.txt")
    (root / "notes.txt").write_text("marks untracked")

    fake = tmp_path / "claude"
    fake.write_text(FAKE_CLAUDE)
    fake.chmod(0o755)
    argv_file = tmp_path / "argv"
    monkeypatch.setenv("FAKE_ARGV", str(argv_file))

    calls = {"status": [], "notes": []}
    monkeypatch.setattr(lr, "CLAUDE_BIN", str(fake))
    monkeypatch.setattr(lr, "RUN_LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(lr, "TASK_LOG", tmp_path / "logs" / "task-looper.log")
    monkeypatch.setattr(lr, "LOG", tmp_path / "logs" / "studio-looper.log")
    monkeypatch.setattr(bot_worktree, "WORKTREES", tmp_path / "wts")
    monkeypatch.setattr(lr, "project_root", lambda prefix: (root, ""))
    monkeypatch.setattr(lr, "set_status", lambda lid, s, to_mark=False:
                        calls["status"].append((lid, s, to_mark)) or True)
    monkeypatch.setattr(lr, "post_note", lambda gid, text: calls["notes"].append((gid, text)))
    monkeypatch.setattr(lr, "notify", lambda msg, priority="normal": None)
    (tmp_path / "logs").mkdir()
    return lr, root, git, argv_file, calls, tmp_path


def task(lid, gid="1001"):
    return MirrorTask(local_id=lid, title=f"{lid} — t", priority="none",
                      looper_status="Queue", order=0, asana_id=gid)


def test_checkout_is_untouched_and_each_task_gets_its_own_worktree(env, monkeypatch):
    lr, root, git, argv_file, calls, tmp = env
    before = (git("rev-parse", "--abbrev-ref", "HEAD"), git("status", "--porcelain"))
    monkeypatch.setenv("FAKE_WORK", "commit")
    monkeypatch.setenv("FAKE_OUTCOME", "COMPLETE")
    for lid in ("BD-7", "BD-8"):
        monkeypatch.setenv("FAKE_LID", lid)
        assert lr.work_task(task(lid), "RUN") == "COMPLETE"

    assert (git("rev-parse", "--abbrev-ref", "HEAD"), git("status", "--porcelain")) == before
    # Mark's staged change is in neither looper commit.
    for lid in ("BD-7", "BD-8"):
        files = git("show", "--name-only", "--format=", f"looper/RUN/{lid}").split()
        assert files == ["work.txt"]
        assert (tmp / "wts" / "BD" / f"looper-RUN-{lid}").is_dir()   # kept: it has a commit
    assert ("BD-7", "Review", True) in calls["status"]
    assert calls["notes"] == []   # the session posts its own note


def test_a_worktree_with_no_commits_is_removed(env, monkeypatch):
    lr, root, git, argv_file, calls, tmp = env
    monkeypatch.setenv("FAKE_LID", "BD-7")
    monkeypatch.setenv("FAKE_OUTCOME", "BLOCKED")
    assert lr.work_task(task("BD-7"), "RUN") == "BLOCKED"
    assert not (tmp / "wts" / "BD" / "looper-RUN-BD-7").exists()
    assert "looper/RUN/BD-7" not in git("branch")
    assert ("BD-7", "Blocked", True) in calls["status"]


def test_no_result_blocks_with_the_runners_own_note(env, monkeypatch):
    lr, root, git, argv_file, calls, tmp = env
    monkeypatch.setenv("FAKE_LID", "BD-7")
    monkeypatch.delenv("FAKE_OUTCOME", raising=False)
    assert lr.work_task(task("BD-7"), "RUN") == "BLOCKED"
    assert calls["notes"] and calls["notes"][0][1].startswith("@mark Blocked:")


def test_the_session_is_confined(env, monkeypatch):
    lr, root, git, argv_file, calls, tmp = env
    monkeypatch.setenv("FAKE_LID", "BD-7")
    monkeypatch.setenv("FAKE_OUTCOME", "COMPLETE")
    lr.work_task(task("BD-7"), "RUN")
    argv = argv_file.read_text().splitlines()
    assert "--dangerously-skip-permissions" not in argv
    assert "--restricted" in argv
    wt = tmp / "wts" / "BD" / "looper-RUN-BD-7"
    assert f"Edit(/{wt}/**)" in argv              # edits only in its own worktree
    assert f"Edit(/{root}/**)" in argv            # and never in the checkout
    assert not any(a.startswith("Bash(git checkout") or a == "Bash" for a in argv)


def test_a_kept_branch_with_client_data_is_reported(env, monkeypatch):
    lr, root, git, argv_file, calls, tmp = env
    monkeypatch.setattr(bot_worktree, "guard_hits", lambda r, base, branch: ["Acme"])
    sent = []
    monkeypatch.setattr(lr, "notify", lambda msg, priority="normal": sent.append((msg, priority)))
    monkeypatch.setenv("FAKE_LID", "BD-7")
    monkeypatch.setenv("FAKE_WORK", "commit")
    monkeypatch.setenv("FAKE_OUTCOME", "COMPLETE")
    lr.work_task(task("BD-7"), "RUN")
    assert any("client data" in m and p == "high" for m, p in sent)


def test_an_unregistered_prefix_is_blocked_without_a_session(env, monkeypatch):
    lr, root, git, argv_file, calls, tmp = env
    monkeypatch.setattr(lr, "project_root", lambda prefix: None)
    assert lr.work_task(task("SL-3"), "RUN") == "BLOCKED"
    assert not argv_file.exists()


def test_the_sandbox_works_in_its_subfolder_of_the_repo(env, monkeypatch):
    lr, root, git, argv_file, calls, tmp = env
    (root / "sub").mkdir()
    (root / "sub" / "keep.txt").write_text("k")
    git("add", "sub")
    git("commit", "-qm", "sub")
    monkeypatch.setattr(lr, "project_root", lambda prefix: (root, "sub"))
    monkeypatch.setenv("FAKE_LID", "SLT-1")
    monkeypatch.setenv("FAKE_OUTCOME", "COMPLETE")
    assert lr.work_task(task("SLT-1"), "RUN") == "COMPLETE"
    prompt = argv_file.read_text().split("\n--model")[0]
    assert str(tmp / "wts" / "SLT" / "looper-RUN-SLT-1" / "sub") in prompt


def test_runner_notes_keep_locations_in_where(env, monkeypatch):
    lr, root, git, argv_file, calls, tmp = env
    monkeypatch.setenv("FAKE_LID", "BD-7")
    monkeypatch.delenv("FAKE_OUTCOME", raising=False)
    lr.work_task(task("BD-7"), "RUN")
    summary, _, where = calls["notes"][0][1].partition(" || Where: ")
    assert "/" not in summary and "~" not in summary and ".log" not in summary
    assert where.startswith("~/logs/studio-looper-run-")


# ---------------------------------------------------------------------------
# Status pushes and the window loop
# ---------------------------------------------------------------------------

def test_set_status_retries_once_when_the_push_is_skipped(tmp_path, monkeypatch):
    import looper_runner as lr
    mirror = tmp_path / "asana-mirror.md"
    mirror.write_text(MIRROR)
    monkeypatch.setattr(lr, "target_mirror", lambda: mirror)
    monkeypatch.setattr(lr, "TASK_LOG", tmp_path / "task.log")
    outs = iter(["  0 push(es)", "  [SL] Pushed to BD-7: ['custom_fields']"])
    monkeypatch.setattr(lr, "sync_target", lambda: next(outs))
    assert lr.set_status("BD-7", "Review", to_mark=True)
    assert parse_mirror_tasks(mirror.read_text())[0].looper_status == "Review"


def test_set_status_warns_when_the_push_never_lands(tmp_path, monkeypatch):
    import looper_runner as lr
    mirror = tmp_path / "asana-mirror.md"
    mirror.write_text(MIRROR)
    monkeypatch.setattr(lr, "target_mirror", lambda: mirror)
    monkeypatch.setattr(lr, "TASK_LOG", tmp_path / "task.log")
    monkeypatch.setattr(lr, "sync_target", lambda: "  0 push(es)")
    assert not lr.set_status("BD-7", "Review")
    assert "push not confirmed" in (tmp_path / "task.log").read_text()


def test_window_works_the_queue_in_order_and_stops_at_the_usage_limit(tmp_path, monkeypatch):
    import looper_runner as lr
    mirror = tmp_path / "asana-mirror.md"
    mirror.write_text(MIRROR)
    monkeypatch.setattr(lr, "target_mirror", lambda: mirror)
    monkeypatch.setattr(lr, "LOG", tmp_path / "runner.log")
    monkeypatch.setattr(lr, "TASK_LOG", tmp_path / "task.log")
    monkeypatch.setattr(lr, "LOCK_DIR", tmp_path)
    monkeypatch.setattr(lr, "presync", lambda: True)
    monkeypatch.setattr(lr, "notify", lambda msg, priority="normal": None)
    monkeypatch.setattr(lr, "usage_pct", lambda: 0)
    worked = []

    def fake_work(t, run_id):
        worked.append(t.local_id)
        if t.local_id == "BD-7":
            mirror.write_text(set_task_fields(mirror.read_text(), "BD-7", {"Looper Status": "Review"}))
            return "COMPLETE"
        return "usage-limit"   # BD-8 stops at the Max limit and stays queued
    monkeypatch.setattr(lr, "work_task", fake_work)
    lr.run_window("test")
    assert worked == ["BD-7", "BD-8"]
    assert "deadline reached" in (tmp_path / "runner.log").read_text()


def test_window_respects_the_usage_cap(tmp_path, monkeypatch):
    import looper_runner as lr
    mirror = tmp_path / "asana-mirror.md"
    mirror.write_text(MIRROR)
    monkeypatch.setattr(lr, "target_mirror", lambda: mirror)
    monkeypatch.setattr(lr, "LOG", tmp_path / "runner.log")
    monkeypatch.setattr(lr, "TASK_LOG", tmp_path / "task.log")
    monkeypatch.setattr(lr, "LOCK_DIR", tmp_path)
    monkeypatch.setattr(lr, "presync", lambda: True)
    monkeypatch.setattr(lr, "notify", lambda msg, priority="normal": None)
    monkeypatch.setattr(lr, "usage_pct", lambda: 80)
    monkeypatch.setattr(lr, "work_task", lambda t, r: pytest.fail("worked past the cap"))
    lr.run_window("test", stop_at_pct=60)


def test_worktree_starts_from_a_named_branch(tmp_path):
    import subprocess
    import bot_worktree
    repo = tmp_path / "repo"
    repo.mkdir()
    g = lambda *a: subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True, check=True)
    g("init", "-q"); g("checkout", "-qb", "develop"); g("config", "user.email", "t@example.test"); g("config", "user.name", "T")
    (repo / "a").write_text("1"); g("add", "a"); g("commit", "-qm", "base")
    g("checkout", "-qb", "looper/x"); (repo / "b").write_text("2"); g("add", "b"); g("commit", "-qm", "looper work")
    g("checkout", "-q", "develop")
    wt, _ = bot_worktree.ensure_worktree(repo, tmp_path / "wt", "bot/T-1", start="looper/x")
    assert (wt / "b").exists()
    wt2, _ = bot_worktree.ensure_worktree(repo, tmp_path / "wt2", "bot/T-2", start="looper/missing")
    assert not (wt2 / "b").exists()
