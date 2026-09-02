"""wise-pulse checkpoint round-trip.

Three bugs shipped in this script because nothing ever exercised the non-network
half of it: a hardcoded cwd, an invalid notifier channel, and a save_checkpoint
that unpacked fetch_balances' 3-tuples as 2-tuples and crashed on every baseline
write. The last one meant the checkpoint file never existed, so every run looked
like a first run and no change was ever detected.

These tests cover the seam between fetch_balances' output shape and everything
downstream of it, without touching the Wise API.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[2] / ".claude" / "skills" / "wise-pulse" / "wise_pulse.py"


@pytest.fixture(scope="module")
def wp():
    spec = importlib.util.spec_from_file_location("wise_pulse", SKILL)
    module = importlib.util.module_from_spec(spec)
    sys.modules["wise_pulse"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def checkpoint_in(tmp_path, wp, monkeypatch):
    path = tmp_path / "balances-checkpoint.json"
    monkeypatch.setattr(wp, "get_checkpoint_path", lambda: path)
    return path


# What fetch_balances actually returns: {balance_id: (balance_obj, amount, currency)}
FETCHED = {
    "93635981": ({"id": 93635981}, 3363.33, "USD"),
    "93635923": ({"id": 93635923}, 238.56, "EUR"),
}


def test_save_checkpoint_accepts_fetch_balances_output(wp, checkpoint_in):
    wp.save_checkpoint(FETCHED)
    assert json.loads(checkpoint_in.read_text()) == {"93635981": 3363.33, "93635923": 238.56}


def test_checkpoint_round_trips(wp, checkpoint_in):
    wp.save_checkpoint(FETCHED)
    assert wp.load_checkpoint() == {"93635981": 3363.33, "93635923": 238.56}


def test_load_checkpoint_empty_before_first_save(wp, checkpoint_in):
    assert wp.load_checkpoint() == {}


def test_load_checkpoint_survives_corrupt_file(wp, checkpoint_in):
    checkpoint_in.write_text("{not json")
    assert wp.load_checkpoint() == {}


def test_saved_checkpoint_detects_a_later_change(wp, checkpoint_in):
    """A saved baseline must compare against the next poll by balance id."""
    wp.save_checkpoint(FETCHED)
    previous = wp.load_checkpoint()

    moved = dict(FETCHED, **{"93635923": ({"id": 93635923}, 200.00, "EUR")})
    changed = [
        bid for bid, (_, amount, _c) in moved.items()
        if previous.get(bid) is not None and amount != previous[bid]
    ]
    assert changed == ["93635923"]


def test_find_account_info_covers_every_configured_balance(wp):
    for account in wp.ACCOUNTS:
        for balance in account["balances"]:
            acc_type, name, currency = wp.find_account_info(str(balance["id"]))
            assert acc_type != "Unknown"
            assert currency == balance["currency"]
