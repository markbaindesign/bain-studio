"""Write side: append transactions to the GnuCash book.

This is the only module that modifies the book, and it will not do so without
an explicit commit. Three guarantees, in order:

1. Nothing is written until a timestamped backup exists alongside the book.
2. Every transaction is checked to balance *before* the file is touched.
3. The written file is re-parsed and its balances re-derived afterwards; if the
   result does not match what was predicted, the backup is restored.

The book uses trading accounts (Trading:CURRENCY:*), so any transaction whose
legs span more than one currency needs a trading leg per real leg carrying the
negated value and quantity. Without them GnuCash reports an imbalance.
"""

import gzip
import os
import re
import shutil
import uuid
from datetime import datetime
from fractions import Fraction
from typing import Dict, List, Tuple

from .book import NS, Book
from .model import Txn, as_gnc_numeric


class WriteRefused(Exception):
    """Raised when a transaction cannot be safely written."""


def _guid() -> str:
    return uuid.uuid4().hex


def _esc(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def expand_legs(txn: Txn, book: Book) -> List[Tuple[str, Fraction, Fraction]]:
    """Resolve a Txn into (account_guid, value, quantity) triples.

    `value` is in the transaction currency; `quantity` is in the account's own
    currency. Adds trading legs when the transaction spans currencies.
    """
    txn_ccy = txn.currency
    out: List[Tuple[str, Fraction, Fraction]] = []
    currencies = {leg.currency for leg in txn.legs}

    for leg in txn.legs:
        acc = book.resolve(leg.account)
        if acc.currency and acc.currency != leg.currency:
            raise WriteRefused(
                "%s is a %s account but the leg is in %s (%s)"
                % (leg.account, acc.currency, leg.currency, txn.description)
            )
        if leg.currency == txn_ccy:
            value = leg.amount
        elif leg.value is not None:
            value = leg.value
        else:
            raise WriteRefused(
                "Cross-currency leg on %r (%s) has no value in %s. The source "
                "adapter must supply both sides of a conversion."
                % (txn.description, leg.currency, txn_ccy)
            )
        out.append((acc.guid, value, leg.amount))

    if len(currencies) > 1:
        if not book.uses_trading_accounts:
            raise WriteRefused(
                "Cross-currency transaction but the book has no trading accounts."
            )
        for leg, (_, value, qty) in zip(txn.legs, list(out)):
            trading = book.trading_account(leg.currency)
            if trading is None:
                raise WriteRefused(
                    "No Trading:CURRENCY:%s account in the book." % leg.currency
                )
            out.append((trading.guid, -value, -qty))

    total = sum(value for _, value, _ in out)
    if total != 0:
        raise WriteRefused(
            "Transaction %r does not balance: values sum to %s %s, not zero."
            % (txn.description, float(total), txn_ccy)
        )
    return out


def render(txn: Txn, book: Book) -> str:
    """Render one Txn as a <gnc:transaction> XML block."""
    legs = expand_legs(txn, book)
    posted = txn.date.strftime("%Y-%m-%d")
    entered = datetime.now().strftime("%Y-%m-%d %H:%M:%S +0000")

    parts = [
        '<gnc:transaction version="2.0.0">',
        '  <trn:id type="guid">%s</trn:id>' % _guid(),
        "  <trn:currency>",
        "    <cmdty:space>CURRENCY</cmdty:space>",
        "    <cmdty:id>%s</cmdty:id>" % txn.currency,
        "  </trn:currency>",
        "  <trn:date-posted>",
        "    <ts:date>%s 10:59:00 +0000</ts:date>" % posted,
        "  </trn:date-posted>",
        "  <trn:date-entered>",
        "    <ts:date>%s</ts:date>" % entered,
        "  </trn:date-entered>",
        "  <trn:description>%s</trn:description>" % _esc(txn.description),
    ]

    notes = " | ".join(p for p in (txn.reference, txn.source_id) if p)
    parts += [
        "  <trn:slots>",
        "    <slot>",
        "      <slot:key>date-posted</slot:key>",
        '      <slot:value type="gdate">',
        "        <gdate>%s</gdate>" % posted,
        "      </slot:value>",
        "    </slot>",
    ]
    if notes:
        parts += [
            "    <slot>",
            "      <slot:key>notes</slot:key>",
            '      <slot:value type="string">%s</slot:value>' % _esc(notes),
            "    </slot>",
        ]
    parts += ["  </trn:slots>", "  <trn:splits>"]

    for guid, value, qty in legs:
        parts += [
            "    <trn:split>",
            '      <split:id type="guid">%s</split:id>' % _guid(),
            "      <split:reconciled-state>n</split:reconciled-state>",
            "      <split:value>%s</split:value>" % as_gnc_numeric(value),
            "      <split:quantity>%s</split:quantity>" % as_gnc_numeric(qty),
            '      <split:account type="guid">%s</split:account>' % guid,
            "    </trn:split>",
        ]

    parts += ["  </trn:splits>", "</gnc:transaction>"]
    return "\n".join(parts)


def backup(book_path: str) -> str:
    """Copy the book into Backups/ with a timestamp. Returns the backup path."""
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backups = os.path.join(os.path.dirname(book_path), "Backups")
    os.makedirs(backups, exist_ok=True)
    dest = os.path.join(
        backups, "%s.bookkeeper-%s.gnucash" % (os.path.basename(book_path), stamp)
    )
    shutil.copy2(book_path, dest)
    return dest


def _lock_present(book_path: str) -> bool:
    return os.path.exists(book_path + ".LCK")


def commit(book_path: str, txns: List[Txn], book: Book) -> Dict:
    """Append transactions to the book. Returns a report dict.

    Refuses if GnuCash currently holds the book open, since that process would
    overwrite whatever is written here when it next saves.
    """
    if _lock_present(book_path):
        raise WriteRefused(
            "The book is open in GnuCash (a .LCK file is present). Close it "
            "first — otherwise GnuCash will overwrite these transactions on "
            "its next save."
        )
    if not txns:
        return {"written": 0, "backup": None}

    # Predict the effect before touching anything, so it can be verified after.
    predicted: Dict[str, Fraction] = {}
    blocks = []
    for txn in txns:
        blocks.append(render(txn, book))
        for leg in txn.legs:
            predicted.setdefault(leg.account, Fraction(0))
            predicted[leg.account] += leg.amount

    before = {path: book.balance(path) for path in predicted}
    backup_path = backup(book_path)

    with open(book_path, "rb") as fh:
        gzipped = fh.read(2) == b"\x1f\x8b"
    opener = gzip.open if gzipped else open
    with opener(book_path, "rt", encoding="utf-8") as fh:
        content = fh.read()

    body = "\n".join(blocks)
    if "</gnc:book>" not in content:
        raise WriteRefused("Unrecognised book structure: no </gnc:book> found.")
    content = content.replace("</gnc:book>", body + "\n</gnc:book>", 1)

    # Keep the transaction count honest — GnuCash warns on a mismatch.
    def bump(match):
        return '<gnc:count-data cd:type="transaction">%d</gnc:count-data>' % (
            int(match.group(1)) + len(txns)
        )

    content, bumped = re.subn(
        r'<gnc:count-data cd:type="transaction">(\d+)</gnc:count-data>', bump,
        content, count=1,
    )
    if not bumped:
        raise WriteRefused("Could not find the transaction count-data element.")

    tmp = book_path + ".bookkeeper.tmp"
    with (gzip.open(tmp, "wt", encoding="utf-8") if gzipped
          else open(tmp, "w", encoding="utf-8")) as fh:
        fh.write(content)
    os.replace(tmp, book_path)

    # Verify: re-read from disk and confirm each balance moved as predicted.
    try:
        after_book = Book(book_path)
        drift = {}
        for path, delta in predicted.items():
            actual = after_book.balance(path) - before[path]
            if actual != delta:
                drift[path] = (float(delta), float(actual))
        if drift:
            raise WriteRefused("Balances did not move as predicted: %s" % drift)
    except Exception:
        shutil.copy2(backup_path, book_path)
        raise

    return {
        "written": len(txns),
        "backup": backup_path,
        "balances": {p: float(after_book.balance(p)) for p in predicted},
    }
