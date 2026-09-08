"""Read side of the GnuCash book: accounts, existing transactions, dedupe.

Reads the gzipped XML book directly. The writer (writer.py) is the only thing
that modifies it, and only via an explicit --commit.
"""

import gzip
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from fractions import Fraction
from typing import Dict, List, Optional, Set, Tuple

NS = {
    "gnc": "http://www.gnucash.org/XML/gnc",
    "act": "http://www.gnucash.org/XML/act",
    "trn": "http://www.gnucash.org/XML/trn",
    "split": "http://www.gnucash.org/XML/split",
    "ts": "http://www.gnucash.org/XML/ts",
    "cmdty": "http://www.gnucash.org/XML/cmdty",
}

# Account types that represent real money and can therefore anchor an import.
BANKISH = {"BANK", "CASH", "CREDIT", "ASSET", "LIABILITY"}


@dataclass
class Account:
    guid: str
    name: str
    type: str
    currency: str
    parent: Optional[str]
    path: str = ""


class Book:
    """An in-memory view of the accounts and transaction signatures in a book."""

    def __init__(self, path: str):
        self.path = path
        self.accounts: Dict[str, Account] = {}
        self.by_path: Dict[str, Account] = {}
        self.signatures: Set[Tuple] = set()
        # (account, amount, currency) -> [dates]. Lets us spot a transaction
        # that is already in the book under a slightly different date: a hand
        # entry is often dated the day it was typed, not the day the bank
        # settled it, and exact-date matching would re-post all of those.
        self.by_amount: Dict[Tuple, List] = {}
        self.txn_count = 0
        self._load()

    # ------------------------------------------------------------------ load

    @staticmethod
    def _read_bytes(path: str) -> bytes:
        with open(path, "rb") as fh:
            magic = fh.read(2)
        opener = gzip.open if magic == b"\x1f\x8b" else open
        with opener(path, "rb") as fh:
            return fh.read()

    def _load(self):
        root = ET.fromstring(self._read_bytes(self.path))

        for el in root.iter("{%s}account" % NS["gnc"]):
            cur = el.find("act:commodity/cmdty:id", NS)
            parent = el.find("act:parent", NS)
            acc = Account(
                guid=el.find("act:id", NS).text,
                name=el.find("act:name", NS).text,
                type=el.find("act:type", NS).text,
                currency=cur.text if cur is not None else "",
                parent=parent.text if parent is not None else None,
            )
            self.accounts[acc.guid] = acc

        for acc in self.accounts.values():
            acc.path = self._path_of(acc.guid)
            # Strip the synthetic root so callers use "Assets:Current Assets:..."
            visible = re.sub(r"^Root Account:", "", acc.path)
            self.by_path[visible] = acc

        for txn in root.iter("{%s}transaction" % NS["gnc"]):
            self.txn_count += 1
            posted = txn.find("trn:date-posted/ts:date", NS)
            if posted is None:
                continue
            day = datetime.strptime(posted.text[:10], "%Y-%m-%d").date()
            for split in txn.iter("{%s}split" % NS["trn"]):
                guid = split.find("split:account", NS).text
                acc = self.accounts.get(guid)
                if acc is None or acc.type not in BANKISH:
                    continue
                qty = Fraction(split.find("split:quantity", NS).text)
                visible = re.sub(r"^Root Account:", "", acc.path)
                self.signatures.add((day, visible, qty, acc.currency))
                self.by_amount.setdefault(
                    (visible, qty, acc.currency), []
                ).append(day)

    def _path_of(self, guid: str, depth: int = 0) -> str:
        acc = self.accounts[guid]
        if acc.parent is None or acc.parent not in self.accounts or depth > 20:
            return acc.name
        return self._path_of(acc.parent, depth + 1) + ":" + acc.name

    # --------------------------------------------------------------- queries

    def account(self, path: str) -> Optional[Account]:
        """Look up an account by its visible path (root stripped)."""
        return self.by_path.get(path)

    def resolve(self, path: str) -> Account:
        acc = self.account(path)
        if acc is None:
            raise KeyError(
                "No such account in the book: %r. Create it in GnuCash first, "
                "or correct the mapping in the rules file." % path
            )
        return acc

    def trading_account(self, currency: str) -> Optional[Account]:
        return self.account("Trading:CURRENCY:%s" % currency)

    @property
    def uses_trading_accounts(self) -> bool:
        return any(a.type == "TRADING" for a in self.accounts.values())

    def balance(self, path: str) -> Fraction:
        """Current balance of one account, in its own currency."""
        acc = self.resolve(path)
        total = Fraction(0)
        root = ET.fromstring(self._read_bytes(self.path))
        for split in root.iter("{%s}split" % NS["trn"]):
            if split.find("split:account", NS).text == acc.guid:
                total += Fraction(split.find("split:quantity", NS).text)
        return total

    def contains(self, txn) -> bool:
        """True if a transaction with this signature is already in the book."""
        return txn.signature() in self.signatures

    def near_duplicate(self, txn, days: int = 3, claimed=None):
        """Find a book entry with the same amount within `days` of this one.

        Hand-entered transactions are frequently dated a day or two off what the
        bank reports — the day they were typed rather than the day they settled.
        Those are real duplicates and exact-date matching sails straight past
        them, so they get surfaced rather than written.

        `claimed` is a set of (key, date) already attributed to another incoming
        transaction, so N identical amounts in the book can absorb at most N
        incoming rows rather than suppressing every one of them.
        """
        leg = txn.primary
        if leg is None:
            return None
        key = (leg.account, leg.amount, leg.currency)
        claimed = claimed if claimed is not None else set()
        candidates = [
            d for d in self.by_amount.get(key, [])
            if (key, d) not in claimed and 0 < abs((d - txn.date).days) <= days
        ]
        if not candidates:
            return None
        best = min(candidates, key=lambda d: abs((d - txn.date).days))
        claimed.add((key, best))
        return best


def default_book_path() -> str:
    """Resolve the book path from the environment, matching the dashboard."""
    for var in ("GNUCASH_FILE", "GNUCASH_PATH"):
        val = os.environ.get(var)
        if val and os.path.exists(val):
            return val
    gdir = os.environ.get("GNUCASH_DIR")
    if gdir:
        guess = os.path.join(gdir, "accounts.gnucash")
        if os.path.exists(guess):
            return guess
    raise SystemExit(
        "Cannot locate the GnuCash book. Set GNUCASH_FILE in studio/.env."
    )
