"""Tests for the bookkeeper.

Everything runs against a synthetic book built in a temp directory — the real
book is private, gitignored, and far too valuable to be a test fixture.

The cases that matter most are the ones that would corrupt the books silently
rather than crash: fee arithmetic, per-currency leaf selection, and the trading
legs that make a cross-currency transaction balance.
"""

import gzip
import os
import re
import sys
from datetime import date
from fractions import Fraction

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from studio.bookkeeper.book import Book
from studio.bookkeeper.categorise import Rules, categorise, resolve_account
from studio.bookkeeper.model import Leg, Txn, as_gnc_numeric, to_fraction
from studio.bookkeeper.pipeline import run
from studio.bookkeeper.sources import wise
from studio.bookkeeper.writer import WriteRefused, commit, expand_legs


# --------------------------------------------------------------- the fixture

ACCOUNTS = [
    ("root", "Root Account", "ROOT", "", None),
    ("assets", "Assets", "ASSET", "EUR", "root"),
    ("wbusd", "Wise Business (USD)", "BANK", "USD", "assets"),
    ("wbeur", "Wise Business (EUR)", "BANK", "EUR", "assets"),
    ("expenses", "Expenses", "EXPENSE", "EUR", "root"),
    ("fees", "Bank Fees", "EXPENSE", "EUR", "expenses"),
    ("feesusd", "Bank Fees (USD)", "EXPENSE", "USD", "fees"),
    ("feeseur", "Bank Fees (EUR)", "EXPENSE", "EUR", "fees"),
    ("software", "Software", "EXPENSE", "EUR", "expenses"),
    ("swusd", "Software (USD)", "EXPENSE", "USD", "software"),
    ("income", "Income", "INCOME", "EUR", "root"),
    ("client", "Client Income", "INCOME", "EUR", "income"),
    ("clientusd", "Client Income (USD)", "INCOME", "USD", "client"),
    ("trading", "Trading", "TRADING", "EUR", "root"),
    ("tccy", "CURRENCY", "TRADING", "EUR", "trading"),
    ("tusd", "USD", "TRADING", "USD", "tccy"),
    ("teur", "EUR", "TRADING", "EUR", "tccy"),
]


def _account_xml(guid, name, type_, currency, parent):
    commodity = ""
    if currency:
        commodity = (
            "  <act:commodity><cmdty:space>CURRENCY</cmdty:space>"
            "<cmdty:id>%s</cmdty:id></act:commodity>\n" % currency
        )
    parent_el = '  <act:parent type="guid">%s</act:parent>\n' % parent if parent else ""
    return (
        '<gnc:account version="2.0.0">\n'
        "  <act:name>%s</act:name>\n"
        '  <act:id type="guid">%s</act:id>\n'
        "  <act:type>%s</act:type>\n"
        "%s%s"
        "</gnc:account>\n" % (name, guid, type_, commodity, parent_el)
    )


@pytest.fixture
def book_path(tmp_path):
    """A minimal but structurally faithful GnuCash book."""
    accounts = "".join(_account_xml(*a) for a in ACCOUNTS)
    xml = (
        '<?xml version="1.0" encoding="utf-8" ?>\n'
        "<gnc-v2\n"
        '     xmlns:gnc="http://www.gnucash.org/XML/gnc"\n'
        '     xmlns:act="http://www.gnucash.org/XML/act"\n'
        '     xmlns:book="http://www.gnucash.org/XML/book"\n'
        '     xmlns:cd="http://www.gnucash.org/XML/cd"\n'
        '     xmlns:cmdty="http://www.gnucash.org/XML/cmdty"\n'
        '     xmlns:slot="http://www.gnucash.org/XML/slot"\n'
        '     xmlns:split="http://www.gnucash.org/XML/split"\n'
        '     xmlns:trn="http://www.gnucash.org/XML/trn"\n'
        '     xmlns:ts="http://www.gnucash.org/XML/ts">\n'
        '<gnc:count-data cd:type="book">1</gnc:count-data>\n'
        '<gnc:book version="2.0.0">\n'
        '<gnc:count-data cd:type="account">%d</gnc:count-data>\n'
        '<gnc:count-data cd:type="transaction">0</gnc:count-data>\n'
        "%s"
        "</gnc:book>\n"
        "</gnc-v2>\n" % (len(ACCOUNTS), accounts)
    )
    path = str(tmp_path / "test.gnucash")
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        fh.write(xml)
    return path


@pytest.fixture
def book(book_path):
    return Book(book_path)


@pytest.fixture
def rules():
    return Rules({
        "rules": [
            {"match": "khyentse", "account": "Income:Client Income", "direction": "in"},
            {"match": "anthropic", "account": "Expenses:Software"},
            {"match": "nowhere", "account": "Expenses:Does Not Exist"},
        ]
    })


WISE_ACCOUNTS = {
    ("business", "USD"): "Assets:Wise Business (USD)",
    ("business", "EUR"): "Assets:Wise Business (EUR)",
}


# ------------------------------------------------------------------- amounts

def test_to_fraction_avoids_float_error():
    # 4.65 as a float is 4.6500000000000003552713678800500929355621337890625
    assert to_fraction(4.65) == Fraction(465, 100)
    assert to_fraction("1,234.56") == Fraction(123456, 100)


def test_gnc_numeric_rounds_half_up():
    assert as_gnc_numeric(Fraction(465, 100)) == "465/100"
    # An FX division can leave a third of a cent; it must not unbalance a split.
    assert as_gnc_numeric(Fraction(1, 3)) == "33/100"
    assert as_gnc_numeric(Fraction(-1, 3)) == "-33/100"


# ------------------------------------------------------------ Wise semantics

def _row(**kw):
    row = {
        "ID": "TRANSFER-1", "Status": "COMPLETED", "Direction": "IN",
        "Created on": "2026-09-01 10:00:00", "Finished on": "2026-09-01 10:00:00",
        "Source fee amount": "", "Source fee currency": "",
        "Source name": "", "Source amount (after fees)": "",
        "Source currency": "USD", "Target name": "",
        "Target amount (after fees)": "", "Target currency": "USD",
        "Reference": "",
    }
    row.update(kw)
    return row


def test_inbound_fee_is_added_back_to_reach_gross():
    """$1,000 sent, $6.11 fee, $993.89 arrives. Income must be the gross."""
    txns = wise.parse_rows([_row(
        Direction="IN",
        **{"Source name": "KHYENTSE FOUNDATION",
           "Source fee amount": "6.11", "Source fee currency": "USD",
           "Target amount (after fees)": "993.89"}
    )], WISE_ACCOUNTS, "business")

    assert len(txns) == 1
    txn = txns[0]
    bank = txn.legs[0]
    assert bank.amount == Fraction(99389, 100)
    fee = [l for l in txn.legs if "Fees" in l.account][0]
    assert fee.amount == Fraction(611, 100)
    # bank + fee = 1000.00, so the contra the categoriser adds is the gross.
    assert sum(l.amount for l in txn.legs) == Fraction(100000, 100)


def test_outbound_gross_is_net_plus_fee():
    txns = wise.parse_rows([_row(
        Direction="OUT", **{"Target name": "Someone",
                            "Source amount (after fees)": "4.65",
                            "Source fee amount": "0.01"}
    )], WISE_ACCOUNTS, "business")
    assert txns[0].legs[0].amount == Fraction(-466, 100)


def test_zero_amount_card_holds_are_skipped():
    txns = wise.parse_rows([_row(
        Direction="OUT", **{"Target name": "Amazon Prime",
                            "Source amount (after fees)": "0.00"}
    )], WISE_ACCOUNTS, "business")
    assert txns == []


def test_pending_rows_are_skipped():
    txns = wise.parse_rows([_row(Status="PENDING", **{
        "Target amount (after fees)": "100.00"})], WISE_ACCOUNTS, "business")
    assert txns == []


def test_conversion_is_balanced_by_construction():
    txns = wise.parse_rows([_row(
        Direction="NEUTRAL", **{"Source currency": "USD", "Target currency": "EUR",
                                "Source amount (after fees)": "1595.37",
                                "Source fee amount": "4.63",
                                "Target amount (after fees)": "1400.00"}
    )], WISE_ACCOUNTS, "business")
    txn = txns[0]
    assert txn.balanced_by_construction
    # Playbook section 3: 1600 debited, 4.63 fee, 1595.37 actually converted.
    assert txn.legs[0].amount == Fraction(-160000, 100)
    dest = [l for l in txn.legs if l.currency == "EUR"][0]
    assert dest.amount == Fraction(140000, 100)
    assert dest.value == Fraction(159537, 100)


# ---------------------------------------------------------------- accounts

def test_resolve_account_picks_the_currency_leaf(book):
    assert resolve_account(book, "Expenses:Bank Fees", "USD") == \
        "Expenses:Bank Fees:Bank Fees (USD)"
    assert resolve_account(book, "Expenses:Bank Fees", "EUR") == \
        "Expenses:Bank Fees:Bank Fees (EUR)"


def test_resolve_account_refuses_a_currency_mismatch(book):
    """No GBP leaf exists, so it must return None rather than the EUR parent."""
    assert resolve_account(book, "Expenses:Bank Fees", "GBP") is None


def test_resolve_account_never_returns_a_trading_account(book):
    assert resolve_account(book, "Trading:CURRENCY:USD", "USD") is None


def test_unmatched_merchant_goes_to_review(book, rules):
    txn = Txn(date=date(2026, 9, 1), description="Some Shop", counterparty="Some Shop")
    txn.legs.append(Leg("Assets:Wise Business (USD)", Fraction(-500, 100), "USD"))
    categorise(txn, rules, book)
    assert txn.needs_review
    assert len(txn.legs) == 1  # nothing invented


def test_rule_naming_a_missing_account_goes_to_review(book, rules):
    txn = Txn(date=date(2026, 9, 1), description="nowhere", counterparty="nowhere")
    txn.legs.append(Leg("Assets:Wise Business (USD)", Fraction(-500, 100), "USD"))
    categorise(txn, rules, book)
    assert txn.needs_review
    assert "create it in GnuCash" in txn.review_reason


def test_direction_scoped_rule_ignores_the_wrong_direction(book, rules):
    """The khyentse rule is inbound-only; a refund out must not match it."""
    txn = Txn(date=date(2026, 9, 1), description="KHYENTSE", counterparty="KHYENTSE")
    txn.legs.append(Leg("Assets:Wise Business (USD)", Fraction(-100, 100), "USD"))
    categorise(txn, rules, book)
    assert txn.needs_review


# ----------------------------------------------------------------- writing

def _anthropic(amount="-20.00"):
    txn = Txn(date=date(2026, 9, 1), description="Anthropic", counterparty="Anthropic")
    txn.legs.append(Leg("Assets:Wise Business (USD)", to_fraction(amount), "USD"))
    return txn


def test_cross_currency_gets_trading_legs_and_balances(book):
    txn = Txn(date=date(2026, 9, 1), description="Convert USD to EUR")
    txn.legs.append(Leg("Assets:Wise Business (USD)", Fraction(-160000, 100), "USD"))
    txn.legs.append(Leg("Expenses:Bank Fees:Bank Fees (USD)", Fraction(463, 100), "USD"))
    txn.legs.append(Leg("Assets:Wise Business (EUR)", Fraction(140000, 100), "EUR",
                        value=Fraction(159537, 100)))

    legs = expand_legs(txn, book)
    assert len(legs) == 6  # 3 real + 3 trading
    assert sum(value for _, value, _ in legs) == 0


def test_unbalanced_transaction_is_refused(book):
    txn = Txn(date=date(2026, 9, 1), description="Wrong")
    txn.legs.append(Leg("Assets:Wise Business (USD)", Fraction(-100), "USD"))
    txn.legs.append(Leg("Expenses:Software:Software (USD)", Fraction(90), "USD"))
    with pytest.raises(WriteRefused):
        expand_legs(txn, book)


def test_leg_in_the_wrong_currency_for_its_account_is_refused(book):
    txn = Txn(date=date(2026, 9, 1), description="Mismatch")
    txn.legs.append(Leg("Assets:Wise Business (USD)", Fraction(-100), "USD"))
    # Software (USD) is a USD account; claiming the leg is EUR must not pass.
    txn.legs.append(Leg("Expenses:Software:Software (USD)", Fraction(100), "EUR"))
    with pytest.raises(WriteRefused):
        expand_legs(txn, book)


def test_commit_writes_backs_up_and_verifies(book_path, book, rules):
    result = run([_anthropic()], book, rules)
    assert result.counts["ready"] == 1

    report = commit(book_path, result.ready, book)
    assert report["written"] == 1
    assert os.path.exists(report["backup"])

    after = Book(book_path)
    assert after.balance("Assets:Wise Business (USD)") == Fraction(-2000, 100)
    assert after.balance("Expenses:Software:Software (USD)") == Fraction(2000, 100)


def test_commit_bumps_the_transaction_count(book_path, book, rules):
    commit(book_path, run([_anthropic()], book, rules).ready, book)
    with gzip.open(book_path, "rt", encoding="utf-8") as fh:
        content = fh.read()
    declared = int(re.search(
        r'<gnc:count-data cd:type="transaction">(\d+)</gnc:count-data>', content).group(1))
    assert declared == 1
    assert content.count("<gnc:transaction ") == 1


def test_rerun_finds_the_transaction_already_present(book_path, book, rules):
    commit(book_path, run([_anthropic()], book, rules).ready, book)
    again = run([_anthropic()], Book(book_path), rules)
    assert again.counts["ready"] == 0
    assert again.counts["duplicates"] == 1


def test_commit_refuses_while_gnucash_holds_the_book(book_path, book, rules):
    open(book_path + ".LCK", "w").close()
    with pytest.raises(WriteRefused) as exc:
        commit(book_path, run([_anthropic()], book, rules).ready, book)
    assert "open in GnuCash" in str(exc.value)


def test_nothing_is_written_when_a_transaction_is_bad(book_path, book):
    """A refusal must leave the book byte-identical, not half-written."""
    before = open(book_path, "rb").read()
    bad = Txn(date=date(2026, 9, 1), description="Bad")
    bad.legs.append(Leg("Assets:Wise Business (USD)", Fraction(-100), "USD"))
    bad.legs.append(Leg("Expenses:Software:Software (USD)", Fraction(-100), "USD"))
    with pytest.raises(WriteRefused):
        commit(book_path, [bad], book)
    assert open(book_path, "rb").read() == before
