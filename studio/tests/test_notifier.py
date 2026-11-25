import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import notifier


def _capture(monkeypatch):
    sent = []

    class R:
        status_code = 200

    monkeypatch.setattr(notifier, "WEBHOOK_URL", "https://hooks.example.test/x")
    monkeypatch.setattr(notifier.requests, "post", lambda url, json, timeout: sent.append(json) or R())
    return sent


def test_normal_and_low_are_dropped_by_default(monkeypatch):
    monkeypatch.delenv("SLACK_MIN_PRIORITY", raising=False)
    sent = _capture(monkeypatch)
    assert notifier.notify("routine", priority="normal") is False
    assert notifier.notify("fyi", priority="low") is False
    assert sent == []


def test_high_and_urgent_still_go(monkeypatch):
    monkeypatch.delenv("SLACK_MIN_PRIORITY", raising=False)
    sent = _capture(monkeypatch)
    assert notifier.notify("crashed", priority="high")
    assert notifier.notify("down", priority="urgent")
    assert len(sent) == 2


def test_floor_can_be_lowered(monkeypatch):
    monkeypatch.setenv("SLACK_MIN_PRIORITY", "low")
    sent = _capture(monkeypatch)
    assert notifier.notify("fyi", priority="low")
    assert len(sent) == 1
