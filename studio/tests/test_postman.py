import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import postman


def _msg(inbox, name, extra=""):
    p = inbox / f"{name}.md"
    p.write_text(f"---\nid: {name}\nfrom: claude\nto: studio\ntype: note\nsubject: Hello\npriority: normal\n{extra}---\n\nBody text\n")
    return p


def _setup(tmp_path, monkeypatch, result=True):
    inbox = tmp_path / "studio" / "inbox"
    inbox.mkdir(parents=True)
    monkeypatch.setattr(postman, "STUDIO_ROOT", tmp_path)
    monkeypatch.setattr(postman, "SCAN_ROOTS", [])
    monkeypatch.setattr(postman, "LOG_FILE", tmp_path / "postman.log")
    monkeypatch.setenv("POSTMAN_NO_PING", "1")
    # Identity now resolves through studio/registry.py, which reads a registry
    # outside this repo. Point it away so these tests exercise the fallback
    # against tmp_path rather than being answered from the real registry.
    monkeypatch.setenv("BAIN_REGISTRY", str(tmp_path / "no-registry.json"))
    monkeypatch.setenv("BAIN_PROJECTS_JSON", str(tmp_path / "no-projects.json"))
    calls = []
    import types
    fake = types.ModuleType("notifier")
    fake.notify = lambda *a, **k: calls.append(k.get("subject")) or result
    monkeypatch.setitem(sys.modules, "notifier", fake)
    return inbox, calls


def test_sweep_notifies_once_and_keeps_message_in_inbox(tmp_path, monkeypatch):
    inbox, calls = _setup(tmp_path, monkeypatch)
    msg = _msg(inbox, "msg-1")
    assert postman.sweep() == 1
    assert msg.exists()
    assert not (inbox / "processed").exists()
    meta, body = postman._parse_message(msg)
    assert meta["notified_at"]
    assert "Body text" in body
    assert postman.sweep() == 0
    assert calls == ["Hello"]


def test_sweep_leaves_message_unstamped_when_slack_fails(tmp_path, monkeypatch):
    inbox, calls = _setup(tmp_path, monkeypatch, result=False)
    msg = _msg(inbox, "msg-1")
    assert postman.sweep() == 0
    assert "notified_at" not in postman._parse_message(msg)[0]


def test_sweep_skips_already_notified(tmp_path, monkeypatch):
    inbox, calls = _setup(tmp_path, monkeypatch)
    _msg(inbox, "msg-1", extra="notified_at: 2026-09-17T08:05:00+00:00\n")
    assert postman.sweep() == 0
    assert calls == []


def test_send_accepts_note_and_stamps_high_priority_after_posting(tmp_path, monkeypatch):
    inbox, calls = _setup(tmp_path, monkeypatch)
    normal = postman.send(to="studio", subject="n", msg_type="note")
    high = postman.send(to="studio", subject="h", priority="high")
    assert "notified_at" not in postman._parse_message(normal)[0]
    assert postman._parse_message(high)[0]["notified_at"]
    assert calls == ["h"]


def test_project_prefix_resolves_through_registry(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    project = tmp_path / "ddev" / "algolia-search"
    project.mkdir(parents=True)
    docs = tmp_path / "docs" / "projects"
    docs.mkdir(parents=True)
    (docs / "asp.md").write_text(f"---\nprefix: ASP\npath: {project}\n---\n")
    dest = postman.send(to="studio", subject="s", project="asp")
    assert dest.parent == project / ".claude" / "inbox"


def test_unknown_project_falls_back_to_studio_inbox(tmp_path, monkeypatch):
    inbox, _ = _setup(tmp_path, monkeypatch)
    assert postman.send(to="studio", subject="s", project="NOPE").parent == inbox


def _fake_tmux(monkeypatch, panes_out):
    calls = []
    def fake(*args):
        calls.append(args)
        if args[0] == "list-panes":
            return panes_out
        if args[0] == "display-message" and "-p" in args:
            return "algolia\t1\n"
        if args[0] == "list-clients":
            return "/dev/pts/1\n"
        return ""
    monkeypatch.setattr(postman, "_tmux", fake)
    monkeypatch.setattr(postman.subprocess, "run", lambda *a, **k: None)
    return calls


def test_ping_alerts_only_claude_panes_in_the_project(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    (project / "sub").mkdir(parents=True)
    other = tmp_path / "other"
    other.mkdir()
    tty = tmp_path / "tty"
    tty.write_text("")
    calls = _fake_tmux(monkeypatch, "\n".join([
        f"%1\t{tty}\tclaude\t{project / 'sub'}\t@1",
        f"%2\t{tty}\tzsh\t{project}\t@2",
        f"%3\t{tty}\tclaude\t{other}\t@3",
    ]))
    panes = postman.ping(project / ".claude" / "inbox", subject="hi", sender="claude-kf")
    assert panes == ["%1"]
    assert tty.read_text() == "\a"
    assert ("rename-window", "-t", "@1", "📬 algolia") in calls
    assert any(c[0] == "display-message" and "-c" in c for c in calls)


def test_ping_finds_nothing_when_tmux_is_missing(tmp_path, monkeypatch):
    def missing(*args):
        raise FileNotFoundError("tmux")
    monkeypatch.setattr(postman, "_tmux", missing)
    monkeypatch.setattr(postman.subprocess, "run", lambda *a, **k: None)
    assert postman.ping(tmp_path / ".claude" / "inbox", subject="hi") == []
