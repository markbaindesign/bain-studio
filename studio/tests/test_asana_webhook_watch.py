"""Watching held by open Claude sessions, and a lapsed watch restarted by a comment
(BSTD-894). Pure rules first, then the listener's worker against temp state with
the Asana calls stubbed out, so nothing here touches the live listener's files."""

import json

import pytest

from asana_webhook_logic import (
    claude_pid,
    idle_expired,
    is_bot_session,
    prefix_for_dir,
    prune_sessions,
)

# ---------------------------------------------------------------------------
# Pure rules
# ---------------------------------------------------------------------------


def test_open_session_holds_the_watch_however_long_mark_is_quiet():
    entry = {"since": 0, "last_activity": 0, "sessions": {"s1": {"pid": 42}}}
    assert not idle_expired(entry, 10 * 86400, 1800)


def test_closed_session_starts_the_idle_timer():
    entry = {"since": 0, "last_activity": 0, "sessions": {"s1": {"pid": 42}}}
    assert prune_sessions(entry, 5000, alive=lambda pid: False)
    assert entry["sessions"] == {} and entry["last_activity"] == 5000
    assert not idle_expired(entry, 5000 + 1799, 1800)
    assert idle_expired(entry, 5000 + 1800, 1800)


def test_prune_keeps_live_sessions_and_later_activity():
    entry = {"last_activity": 9000, "sessions": {"a": {"pid": 1}, "b": {"pid": 2}}}
    assert prune_sessions(entry, 5000, alive=lambda pid: pid == 1)
    assert list(entry["sessions"]) == ["a"] and entry["last_activity"] == 9000
    assert not prune_sessions(entry, 6000, alive=lambda pid: True)


def test_bot_sessions_are_recognised(tmp_path):
    wt = tmp_path / "bain-bot-worktrees"
    (wt / "BD" / "BD-1").mkdir(parents=True)
    assert is_bot_session({"BAIN_BOT_RUN": "1"}, "/anywhere", str(wt))
    assert is_bot_session({"LOOPER_RUN_ID": "20261119-0200"}, "/anywhere", str(wt))
    assert is_bot_session({}, str(wt / "BD" / "BD-1"), str(wt))
    assert not is_bot_session({}, str(tmp_path), str(wt))


def test_prefix_for_dir_prefers_the_deepest_root(tmp_path):
    studio = tmp_path / "studio"
    (studio / "looper" / "x").mkdir(parents=True)
    roots = {"BSTD": studio, "SL": studio / "looper"}
    assert prefix_for_dir(str(studio / "docs"), roots) == "BSTD"
    assert prefix_for_dir(str(studio / "looper" / "x"), roots) == "SL"
    assert prefix_for_dir(str(tmp_path), roots) is None
    # A sibling whose name merely starts the same is not inside.
    (tmp_path / "studio-other").mkdir()
    assert prefix_for_dir(str(tmp_path / "studio-other"), roots) is None


def test_claude_pid_is_the_nearest_claude_ancestor():
    assert claude_pid([(10, "zsh"), (9, "claude"), (5, "python3"), (3, "claude")]) == 9
    assert claude_pid([(10, "bash"), (1, "systemd")]) is None


# ---------------------------------------------------------------------------
# Listener worker, against temp state
# ---------------------------------------------------------------------------

MARK, PMBOT = "200", "300"


@pytest.fixture
def hook(tmp_path, monkeypatch):
    import asana_webhook as aw

    state = tmp_path / "state"
    for name, rel in (("STATE", ""), ("QUEUE", "queue"), ("WATCH", "watch.json"),
                      ("LAPSED", "lapsed.json"), ("HISTORY", "history.json"),
                      ("LOG", "webhook.log")):
        monkeypatch.setattr(aw, name, state / rel if rel else state)
    monkeypatch.setattr(aw.sync, "USER_GID", MARK)
    monkeypatch.setattr(aw, "project_map", lambda: {"BD": object()})
    monkeypatch.setattr(aw, "_notify", lambda *a, **k: None)
    alive = set()
    monkeypatch.setattr(aw, "_claude_alive", lambda pid: pid in alive)
    aw._test_alive = alive
    return aw


def _watch(aw):
    return json.loads(aw.WATCH.read_text() or "{}") if aw.WATCH.exists() else {}


def test_session_queued_by_hook_starts_watch_and_holds_it(hook, monkeypatch):
    aw = hook
    started = []

    def fake_start(prefix):
        started.append(prefix)
        aw._locked_json(aw.WATCH, lambda d: d.update({prefix: {"since": 0, "last_activity": 0}}))
        return True, "ok"

    monkeypatch.setattr(aw, "start_watch", fake_start)
    aw._test_alive.add(4242)
    aw.enqueue({"prefix": "BD", "source": "session", "session": "s1", "pid": 4242})
    w = aw.Worker()
    w.tick()
    assert started == ["BD"]
    assert "s1" in _watch(aw)["BD"]["sessions"]
    # Hours later with no Asana activity, the open session still holds the watch.
    monkeypatch.setattr(aw.time, "time", lambda: 10 * 3600)
    w.tick()
    assert "BD" in _watch(aw)
    # The session dies without SessionEnd: watching ends 30 minutes later, not before.
    aw._test_alive.clear()
    w.tick()
    assert "BD" in _watch(aw) and _watch(aw)["BD"]["sessions"] == {}
    monkeypatch.setattr(aw.time, "time", lambda: 10 * 3600 + aw.IDLE_S)
    w.tick()
    assert "BD" not in _watch(aw)
    assert "BD" in json.loads(aw.LAPSED.read_text())


def test_session_that_closed_before_the_worker_saw_it_starts_nothing(hook, monkeypatch):
    aw = hook
    monkeypatch.setattr(aw, "start_watch", lambda p: pytest.fail("must not watch"))
    aw.enqueue({"prefix": "BD", "source": "session", "session": "s1", "pid": 999})
    aw.Worker().tick()
    assert _watch(aw) == {}


def test_marks_comment_on_a_lapsed_project_rewatches_and_queues(hook, monkeypatch):
    aw = hook
    aw._locked_json(aw.LAPSED, lambda d: d.update({"BD": 1}))
    monkeypatch.setattr(aw, "resolve", lambda item: {"T1"})
    aw.enqueue({"prefix": "BD", "source": "lapsed",
                "events": [{"user": {"gid": MARK}}]})
    w = aw.Worker()
    w.tick()
    assert "BD" in _watch(aw)
    assert "BD" not in json.loads(aw.LAPSED.read_text())
    assert w.pending["T1"]["prefix"] == "BD"


def test_pmbot_or_non_bot_task_does_not_rewatch(hook, monkeypatch):
    aw = hook
    aw._locked_json(aw.LAPSED, lambda d: d.update({"BD": 1}))
    monkeypatch.setattr(aw, "resolve", lambda item: {"T1"})
    aw.enqueue({"prefix": "BD", "source": "lapsed", "events": [{"user": {"gid": PMBOT}}]})
    aw.Worker().tick()
    assert _watch(aw) == {}
    monkeypatch.setattr(aw, "resolve", lambda item: set())
    aw.enqueue({"prefix": "BD", "source": "lapsed", "events": [{"user": {"gid": MARK}}]})
    aw.Worker().tick()
    assert _watch(aw) == {}


def test_unwatch_is_not_a_lapse(hook):
    aw = hook
    aw._locked_json(aw.WATCH, lambda d: d.update({"BD": {"since": 0}}))
    aw._locked_json(aw.LAPSED, lambda d: d.update({"BD": 1}))
    aw.unwatch("BD")
    assert json.loads(aw.LAPSED.read_text()) == {}


def test_session_end_hook_starts_the_timer(hook, monkeypatch):
    import io

    aw = hook
    aw._locked_json(aw.WATCH, lambda d: d.update(
        {"BD": {"since": 0, "last_activity": 0, "sessions": {"s1": {"pid": 1}}}}))
    monkeypatch.setattr(aw, "_hook_prefix", lambda data: "BD")
    monkeypatch.setattr(aw.sys, "stdin", io.StringIO(json.dumps({"session_id": "s1"})))
    monkeypatch.setattr(aw.time, "time", lambda: 777)
    aw.session_end()
    assert _watch(aw)["BD"] == {"since": 0, "last_activity": 777, "sessions": {}}


def test_bot_run_hook_records_nothing(hook, monkeypatch, tmp_path):
    import io

    aw = hook
    monkeypatch.setenv("BAIN_BOT_RUN", "1")
    monkeypatch.setattr(aw.sys, "stdin", io.StringIO(json.dumps(
        {"session_id": "s1", "cwd": str(tmp_path)})))
    monkeypatch.setattr(aw, "_ancestors", lambda: [(4242, "claude")])
    aw.session_start()
    assert not aw.QUEUE.exists() or not list(aw.QUEUE.glob("*.json"))


# ---------------------------------------------------------------------------
# Hook installer
# ---------------------------------------------------------------------------


def test_installer_adds_both_hooks_once_and_keeps_the_rest():
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "install_watch_hooks", Path(__file__).parent.parent / "scripts" / "install-watch-hooks.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    other = {"hooks": [{"type": "command", "command": "python3 session-log.py"}]}
    settings = {"model": "opus", "hooks": {"SessionEnd": [other]}}
    assert mod.add_hooks(settings, Path("/ops/studio/asana_webhook.py")) == ["SessionStart", "SessionEnd"]
    assert settings["model"] == "opus" and settings["hooks"]["SessionEnd"][0] == other
    start = settings["hooks"]["SessionStart"][0]["hooks"][0]
    assert start["async"] is True and "asana_webhook.py session-start" in start["command"]
    assert mod.add_hooks(settings, Path("/elsewhere/studio/asana_webhook.py")) == []
