import datetime as dt
import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))

GESTOR = "Root Account:Expenses:Gestor"


@pytest.fixture
def parser(monkeypatch, tmp_path):
    # gnucash_parser reads recurring-transactions.yaml at import time.
    (tmp_path / "recurring-transactions.yaml").write_text("recurring: []\n")
    monkeypatch.setenv("FINANCE_CONFIG_DIR", str(tmp_path))
    import gnucash_parser
    return importlib.reload(gnucash_parser)


def test_gestor_next_quarter_follows_last_paid(parser):
    # 14 Aug pays Q2, so Q3 is next: 16 Oct, not 14 Aug + 3 months.
    rows = [{"date": "2026-08-14", "path": GESTOR, "eur": 212.0}]
    got = parser._gestor_upcoming(rows, dt.date(2026, 10, 8))
    assert [(e["date"], e["quarter"], e["amount"]) for e in got] == [("2026-10-16", "Q3 2026", 212.0)]


def test_gestor_paid_quarter_is_not_forecast_again(parser):
    rows = [{"date": "2026-08-14", "path": GESTOR, "eur": 212.0},
            {"date": "2026-10-16", "path": GESTOR, "eur": 212.0}]
    got = parser._gestor_upcoming(rows, dt.date(2026, 10, 20))
    assert [e["date"] for e in got] == ["2027-01-16"]


def test_gestor_due_but_not_booked_is_expected_tomorrow(parser):
    rows = [{"date": "2026-08-14", "path": GESTOR, "eur": 212.0}]
    got = parser._gestor_upcoming(rows, dt.date(2026, 10, 20))
    assert got[0]["date"] == "2026-10-21"
