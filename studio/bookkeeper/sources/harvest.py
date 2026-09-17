"""Harvest adapter — raises invoices into the book.

Every other source here reads a bank feed: money that has already moved. This
one is different. It reads invoices, which is when income is *recognised*, and
that happens before the money arrives:

    issue    DR Accounts Receivable (CCY)   CR Income:Client Income (CCY)
    payment  DR Bank                        CR Accounts Receivable (CCY)

The bank adapters book the second half. Without this one they clear receivables
that were never raised, which drives Accounts Receivable negative and leaves the
income unrecorded in the quarter it belongs to — exactly what happened to the
2026-08-31 Khyentse invoice, found when AR went to −1,000.00.

Both legs are known, so nothing here needs a categorisation rule.
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

from ..model import Leg, Txn, to_fraction

RECEIVABLE = "Assets:Future Assets:Accounts Receivable"
INCOME = "Income:Client Income"


def _client():
    """The dashboard's Harvest client, which already knows the API shape."""
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dashboard = os.path.join(here, "dashboard")
    if dashboard not in sys.path:
        sys.path.insert(0, dashboard)
    from harvest_client import HarvestClient  # noqa: E402

    token = os.environ.get("HARVEST_TOKEN")
    account = os.environ.get("HARVEST_ACCOUNT_ID")
    if not token or not account:
        raise SystemExit(
            "HARVEST_TOKEN and HARVEST_ACCOUNT_ID must be set in studio/.env"
        )
    return HarvestClient(token, account)


def invoices(start: str, end: str, receivable: str = RECEIVABLE,
             income: str = INCOME) -> List[Txn]:
    """Every invoice issued in the range, as an income-recognition transaction.

    State is deliberately ignored. An invoice is income in the quarter it was
    *issued*, whether or not it has been paid — the accrual basis the tax-prep
    skill works on.
    """
    out: List[Txn] = []

    for inv in _client().get_invoices_in_range(start, end):
        issued = inv.get("issue_date")
        amount = to_fraction(inv.get("amount") or 0)
        currency = (inv.get("currency") or "").upper()
        if not issued or amount == 0 or not currency:
            continue

        number = str(inv.get("number") or "")
        client = inv.get("client") or ""

        txn = Txn(
            date=datetime.strptime(issued[:10], "%Y-%m-%d").date(),
            description="Invoice %s - %s" % (number, client) if number else client,
            source="harvest",
            source_id=number,
            reference="invoice %s" % number,
            counterparty=client,
        )
        # Receivable leads, so the dedupe signature keys on it — the same
        # account the bank adapters clear against.
        txn.legs.append(Leg(receivable, amount, currency))
        txn.legs.append(Leg(income, -amount, currency))
        txn.balanced_by_construction = True
        out.append(txn)

    return out
