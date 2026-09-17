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
