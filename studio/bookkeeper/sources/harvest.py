"""Harvest adapter — raises invoices into the book.

Every other source here reads a bank feed: money that has already moved. This
one is different. It reads invoices, which is when income is *recognised*, and
that happens before the money arrives:

    issue    DR Accounts Receivable (CCY)   CR Income:Client Income (CCY)
    payment  DR Bank                        CR Accounts Receivable (CCY)

A Spanish invoice carries IVA and an IRPF retention, and is split (codex s.4):

    DR Accounts Receivable   amount due (total, net of the IRPF)
    DR IRPF Retenido         the retention
    CR Client Income         the pre-tax subtotal
    CR IVA Repercutido       the IVA

An invoice with no tax keeps the two-leg form.

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
IVA = "Liabilities:IVA Repercutido"
IRPF = "Assets:Future Assets:IRPF Retenido"


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


def build_legs(amount, tax, tax2, currency: str, receivable: str = RECEIVABLE,
               income: str = INCOME, iva: str = IVA, irpf: str = IRPF) -> List[Leg]:
    """The legs for one invoice, given its total and its two tax amounts.

    `tax2` is negative for a retention, so subtotal = amount - tax - tax2 holds
    whatever the signs. The receivable stays at `amount`, which is what the
    client actually owes and later pays.
    """
    if tax == 0 and tax2 == 0:
        return [Leg(receivable, amount, currency), Leg(income, -amount, currency)]
    subtotal = amount - tax - tax2
    legs = [Leg(receivable, amount, currency)]
    if tax2:
        legs.append(Leg(irpf, -tax2, currency))
    legs.append(Leg(income, -subtotal, currency))
    if tax:
        legs.append(Leg(iva, -tax, currency))
    return legs


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
        tax = to_fraction(inv.get("tax_amount") or 0)
        tax2 = to_fraction(inv.get("tax2_amount") or 0)
        txn.legs += build_legs(amount, tax, tax2, currency, receivable, income)
        if tax2 > 0:
            # A retention is negative. A positive second tax is something
            # else, and books as a debit to IRPF Retenido, which would be wrong.
            txn.needs_review = True
            txn.review_reason = "Second tax on the invoice is positive, not a retention"
        txn.balanced_by_construction = True
        out.append(txn)

    return out
