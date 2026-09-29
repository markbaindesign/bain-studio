import importlib.util
import json
import logging
from pathlib import Path

import pytest

pytest.importorskip("algoliasearch")

SCRIPT = Path(__file__).resolve().parents[2] / ".claude" / "skills" / "algolia-pulse" / "algolia_pulse.py"
_spec = importlib.util.spec_from_file_location("algolia_pulse", SCRIPT)
pulse_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pulse_mod)

CONFIG = {"apps": [{"name": "app", "app_id": "APPID", "admin_api_key": "k",
                    "indices": [{"name": "wp_global", "query": "*"}]}]}


@pytest.fixture
def config_file(tmp_path):
    p = tmp_path / "pulse-config.json"
    p.write_text(json.dumps(CONFIG))
    p.chmod(0o600)
    return p


@pytest.fixture(autouse=True)
def no_real_log(monkeypatch):
    # pulse() logs to ~/.algolia/pulse.log; keep tests off the real file
    monkeypatch.setattr(pulse_mod, "setup_logging", lambda *a, **k: logging.getLogger("test-pulse"))


def test_load_config_accepts_owner_only_file(config_file):
    assert pulse_mod.load_config(str(config_file))["apps"][0]["name"] == "app"


@pytest.mark.parametrize("mode", [0o644, 0o640, 0o604, 0o660, 0o666])
def test_load_config_refuses_file_readable_by_others(config_file, mode):
    config_file.chmod(mode)
    with pytest.raises(ValueError, match="chmod 600"):
        pulse_mod.load_config(str(config_file))


def test_load_config_missing_file_still_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        pulse_mod.load_config(str(tmp_path / "nope.json"))


def test_pulse_bad_permissions_exits_1_and_alerts_slack(config_file, monkeypatch):
    config_file.chmod(0o644)
    sent = []
    monkeypatch.setattr(pulse_mod, "_send_slack", lambda *a: sent.append(a))
    assert pulse_mod.pulse(str(config_file)) == 1
    message, details, priority = sent[0]
    assert "cannot run" in message and "chmod 600" in details and priority == "high"


def test_pulse_bad_permissions_no_alert_when_notify_off(config_file, monkeypatch):
    config_file.chmod(0o644)
    sent = []
    monkeypatch.setattr(pulse_mod, "_send_slack", lambda *a: sent.append(a))
    assert pulse_mod.pulse(str(config_file), notify=False) == 1
    assert sent == []


def test_pulse_dry_run_never_alerts(config_file, monkeypatch):
    config_file.chmod(0o644)
    sent = []
    monkeypatch.setattr(pulse_mod, "_send_slack", lambda *a: sent.append(a))
    assert pulse_mod.pulse(str(config_file), dry_run=True) == 1
    assert sent == []


def test_pulse_missing_config_alerts_slack(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(pulse_mod, "_send_slack", lambda *a: sent.append(a))
    assert pulse_mod.pulse(str(tmp_path / "nope.json")) == 1
    assert len(sent) == 1
