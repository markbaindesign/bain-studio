import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "ivas-prep"))

from upwork_check import same_client, uninvoiced, upwork_earnings

HEADER = ("Date,Transaction ID,Transaction type,Transaction summary,Transaction summary details,"
          "Description 1,Description 2,Description 3,Agency team,Freelancer,Client team,"
          "Account name,PO,Ref ID,Amount $,Amount in local currency,Currency,Current balance $,"
          "Payment method\n")


def _row(when, kind, client, amount):
    return f'"{when}",1,{kind},Job,,,,,,Mark Bain,{client},Mark Bain,,1,{amount},,,0,\n'


def test_same_client_matches_loosely():
    assert same_client("TECHSTYLE", "TECHSTYLE Accessories B.V.")
    assert same_client("ebiz global", "Ebiz Global")
    assert same_client("Good To Great Schools Australia", "Good To Great Schools")
    assert not same_client("Natural Elements Coaching", "Khyentse Foundation")


def test_flags_paid_client_without_invoice(tmp_path):
    csv = tmp_path / "2026-10-02_transaction_report.csv"
    csv.write_text(HEADER
                   + _row("Oct 2, 2026", "Hourly", "ebiz global", "183.33")        # Q4, ignored
                   + _row("Sep 25, 2026", "Hourly", "ebiz global", "229.17")
                   + _row("Sep 11, 2026", "Hourly", "ebiz global", "128.33")
                   + _row("Sep 25, 2026", "Service Fee", "ebiz global", "-22.92")  # not earnings
                   + _row("Aug 7, 2026", "Fixed-price", "TECHSTYLE", "300.00"))
    earnings, latest = upwork_earnings(csv, date(2026, 7, 1), date(2026, 9, 30))
    assert latest == date(2026, 10, 2)
    assert round(earnings["ebiz global"][0], 2) == 357.50
    assert earnings["ebiz global"][1:] == (date(2026, 9, 11), date(2026, 9, 25))
    missing = uninvoiced(earnings, ["TECHSTYLE Accessories B.V.", "Natural Elements Coaching"])
    assert list(missing) == ["ebiz global"]
