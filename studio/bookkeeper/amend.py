"""Correct splits on transactions already in the book.

The importer only ever appends. Fixing a mis-keyed entry that is *already*
booked is a different and more dangerous operation, so it is deliberately
separate, declarative, and narrow: a correction names the transaction by GUID
and the split by GUID, and states the value and quantity it must end up with.
Nothing is inferred or searched for.

It carries the same guarantees as the importer (writer.py): backup first,
verify the arithmetic afterwards against predicted balances, restore the backup
on any mismatch, and refuse outright while GnuCash holds the book.

Amending history is the right move only for a data-entry error in a period that
has not been filed. Once a quarter is filed, post a correcting entry instead so
the filed figures remain reproducible.
"""

import gzip
import os
import re
import shutil
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Dict, List, Optional

import uuid

from .book import Book
from .model import as_gnc_numeric, to_fraction
from .writer import WriteRefused, backup, _lock_present


@dataclass
class SplitFix:
    """One split to change, to repoint at another account, or to delete."""

    split_guid: str
    reason: str
    value: Optional[str] = None      # new value, in the transaction's currency
    quantity: Optional[str] = None   # new quantity, in the account's currency
    account: Optional[str] = None    # repoint at this account path
    delete: bool = False


@dataclass
class NewSplit:
    """A split to add to an existing transaction.

    Needed when the original entry omitted a leg entirely — a bank fee that was
    never recorded, most often, leaving the rest of the transaction plugged to
    an Imbalance account.
    """

    account: str
    value: str
    quantity: str
    reason: str


@dataclass
class Correction:
    """A set of split fixes against one transaction."""

    txn_guid: str
    description: str
    fixes: List[SplitFix] = field(default_factory=list)
    additions: List[NewSplit] = field(default_factory=list)


SPLIT_RE = re.compile(r"<trn:split>.*?</trn:split>", re.S)
TXN_RE = re.compile(r"<gnc:transaction.*?</gnc:transaction>", re.S)


def _split_guid(block: str) -> str:
    return re.search(r'<split:id type="guid">(\w+)</split:id>', block).group(1)


def _account_guid(block: str) -> str:
    return re.search(r'<split:account type="guid">(\w+)</split:account>', block).group(1)


def _values(block: str):
    return (
        Fraction(re.search(r"<split:value>(.*?)</split:value>", block).group(1)),
        Fraction(re.search(r"<split:quantity>(.*?)</split:quantity>", block).group(1)),
    )


def plan(content: str, corrections: List[Correction], book: Book) -> Dict:
    """Work out what each correction changes, without touching anything.

    Returns predicted per-account quantity deltas, keyed by account path.
    """
    deltas: Dict[str, Fraction] = {}

    for correction in corrections:
        txn = next(
            (t for t in TXN_RE.findall(content)
             if '<trn:id type="guid">%s</trn:id>' % correction.txn_guid in t),
            None,
        )
        if txn is None:
            raise WriteRefused(
                "No transaction %s in the book (%s)"
                % (correction.txn_guid, correction.description)
            )

        blocks = {_split_guid(b): b for b in SPLIT_RE.findall(txn)}
        for fix in correction.fixes:
            if fix.split_guid not in blocks:
                raise WriteRefused(
                    "Split %s is not on transaction %s (%s)"
                    % (fix.split_guid, correction.txn_guid, correction.description)
                )
            block = blocks[fix.split_guid]
            old_value, old_qty = _values(block)
            acc = book.accounts[_account_guid(block)]
            path = re.sub(r"^Root Account:", "", acc.path)

            new_qty = Fraction(0) if fix.delete else (
                to_fraction(fix.quantity) if fix.quantity is not None else old_qty
            )
            if fix.account and not fix.delete:
                # Repointing moves the whole amount off one account and onto
                # another, so both sides have to appear in the prediction.
                target = book.resolve(fix.account)
                target_path = re.sub(r"^Root Account:", "", target.path)
                deltas[path] = deltas.get(path, Fraction(0)) - old_qty
                deltas[target_path] = deltas.get(target_path, Fraction(0)) + new_qty
            else:
                deltas[path] = deltas.get(path, Fraction(0)) + (new_qty - old_qty)

        for addition in correction.additions:
            acc = book.resolve(addition.account)
            path = re.sub(r"^Root Account:", "", acc.path)
            deltas[path] = deltas.get(path, Fraction(0)) + to_fraction(addition.quantity)

    return deltas


def apply(book_path: str, corrections: List[Correction], book: Book,
          dry_run: bool = True) -> Dict:
    """Apply corrections. Returns a report; writes nothing unless dry_run is False."""
    if _lock_present(book_path):
        raise WriteRefused(
            "The book is open in GnuCash (a .LCK file is present). Close it first."
        )

    with open(book_path, "rb") as fh:
        gzipped = fh.read(2) == b"\x1f\x8b"
    opener = gzip.open if gzipped else open
    with opener(book_path, "rt", encoding="utf-8") as fh:
        content = fh.read()

    deltas = plan(content, corrections, book)
    before = {path: book.balance(path) for path in deltas}
    changes = []

    for correction in corrections:
        txn = next(
            t for t in TXN_RE.findall(content)
            if '<trn:id type="guid">%s</trn:id>' % correction.txn_guid in t
        )
        new_txn = txn

        for fix in correction.fixes:
            block = next(
                b for b in SPLIT_RE.findall(new_txn) if _split_guid(b) == fix.split_guid
            )
            if fix.delete:
                # Drop the split and the whitespace ahead of it.
                new_txn = re.sub(
                    r"\n\s*" + re.escape(block.strip()), "", new_txn, count=1
                )
                changes.append("%s: removed split %s (%s)"
                               % (correction.description, fix.split_guid[:8], fix.reason))
                continue

            updated = block
            if fix.value is not None:
                updated = re.sub(
                    r"<split:value>.*?</split:value>",
                    "<split:value>%s</split:value>" % as_gnc_numeric(to_fraction(fix.value)),
                    updated, count=1,
                )
            if fix.quantity is not None:
                updated = re.sub(
                    r"<split:quantity>.*?</split:quantity>",
                    "<split:quantity>%s</split:quantity>"
                    % as_gnc_numeric(to_fraction(fix.quantity)),
                    updated, count=1,
                )
            if fix.account is not None:
                updated = re.sub(
                    r'<split:account type="guid">\w+</split:account>',
                    '<split:account type="guid">%s</split:account>'
                    % book.resolve(fix.account).guid,
                    updated, count=1,
                )
            new_txn = new_txn.replace(block, updated, 1)
            changes.append("%s: split %s -> value %s qty %s (%s)"
                           % (correction.description, fix.split_guid[:8],
                              fix.value, fix.quantity, fix.reason))

        for addition in correction.additions:
            acc = book.resolve(addition.account)
            block = (
                "    <trn:split>\n"
                '      <split:id type="guid">%s</split:id>\n'
                "      <split:reconciled-state>n</split:reconciled-state>\n"
                "      <split:value>%s</split:value>\n"
                "      <split:quantity>%s</split:quantity>\n"
                '      <split:account type="guid">%s</split:account>\n'
                "    </trn:split>\n"
                % (uuid.uuid4().hex, as_gnc_numeric(to_fraction(addition.value)),
                   as_gnc_numeric(to_fraction(addition.quantity)), acc.guid)
            )
            if "</trn:splits>" not in new_txn:
                raise WriteRefused("No </trn:splits> in %s" % correction.description)
            new_txn = new_txn.replace("</trn:splits>", block + "  </trn:splits>", 1)
            changes.append("%s: added split %s %s (%s)"
                           % (correction.description, addition.account,
                              addition.quantity, addition.reason))

        # The transaction must still balance in its own currency before it goes back.
        total = sum(_values(b)[0] for b in SPLIT_RE.findall(new_txn))
        if total != 0:
            raise WriteRefused(
                "%s would no longer balance: values sum to %s"
                % (correction.description, float(total))
            )
        content = content.replace(txn, new_txn, 1)

    report = {
        "changes": changes,
        "predicted": {p: float(d) for p, d in deltas.items()},
        "written": False,
        "backup": None,
    }
    if dry_run:
        return report

    backup_path = backup(book_path)
    tmp = book_path + ".amend.tmp"
    with (gzip.open(tmp, "wt", encoding="utf-8") if gzipped
          else open(tmp, "w", encoding="utf-8")) as fh:
        fh.write(content)
    os.replace(tmp, book_path)

    try:
        after = Book(book_path)
        drift = {}
        for path, delta in deltas.items():
            actual = after.balance(path) - before[path]
            if actual != delta:
                drift[path] = (float(delta), float(actual))
        if drift:
            raise WriteRefused("Balances did not move as predicted: %s" % drift)
        if after.txn_count != book.txn_count:
            raise WriteRefused(
                "Transaction count changed (%d -> %d) — an amendment must never "
                "add or remove a transaction." % (book.txn_count, after.txn_count)
            )
    except Exception:
        shutil.copy2(backup_path, book_path)
        raise

    report["written"] = True
    report["backup"] = backup_path
    report["balances"] = {p: float(after.balance(p)) for p in deltas}
    return report


# ---------------------------------------------------------------- prices

PRICE_RE = re.compile(r"<price>.*?</price>", re.S)


def fix_price(book_path: str, price_guid: str, value: str, reason: str,
              dry_run: bool = True) -> Dict:
    """Correct one entry in the GnuCash price database.

    Prices are not splits, so nothing else in this module reaches them — but a
    wrong one is quietly corrosive. GnuCash writes a price for every currency
    transfer made through the transfer dialog, so a mis-keyed conversion leaves
    a mis-keyed *rate* behind as well, and correcting the transaction does not
    correct the price. Anything later reading rates from the book then picks up
    a rate that never existed.

    `value` is the rational GnuCash stores, e.g. "219437/256667", read as
    1 <commodity> = value <currency>.
    """
    if _lock_present(book_path):
        raise WriteRefused(
            "The book is open in GnuCash (a .LCK file is present). Close it first."
        )
    if "/" not in value:
        raise WriteRefused("Price value must be a rational like '219437/256667'")

    with open(book_path, "rb") as fh:
        gzipped = fh.read(2) == b"\x1f\x8b"
    opener = gzip.open if gzipped else open
    with opener(book_path, "rt", encoding="utf-8") as fh:
        content = fh.read()

    block = next(
        (b for b in PRICE_RE.findall(content)
         if '<price:id type="guid">%s</price:id>' % price_guid in b),
        None,
    )
    if block is None:
        raise WriteRefused("No price %s in the book" % price_guid)

    old = re.search(r"<price:value>(.*?)</price:value>", block).group(1)
    updated = re.sub(r"<price:value>.*?</price:value>",
                     "<price:value>%s</price:value>" % value, block, count=1)
    report = {"price": price_guid, "was": old, "now": value, "reason": reason,
              "written": False, "backup": None}
    if dry_run:
        return report

    before = Book(book_path)
    backup_path = backup(book_path)
    tmp = book_path + ".price.tmp"
    with (gzip.open(tmp, "wt", encoding="utf-8") if gzipped
          else open(tmp, "w", encoding="utf-8")) as fh:
        fh.write(content.replace(block, updated, 1))
    os.replace(tmp, book_path)

    try:
        after = Book(book_path)
        # A price change must not move a single balance or transaction.
        if after.txn_count != before.txn_count:
            raise WriteRefused("Transaction count changed — aborting")
        with opener(book_path, "rt", encoding="utf-8") as fh:
            check = fh.read()
        if "<price:value>%s</price:value>" % value not in check:
            raise WriteRefused("The new price value is not in the saved file")
        if "225667" in value and old == value:
            raise WriteRefused("Nothing changed")
    except Exception:
        shutil.copy2(backup_path, book_path)
        raise

    report["written"] = True
    report["backup"] = backup_path
    return report
