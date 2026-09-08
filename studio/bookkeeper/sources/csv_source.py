"""Generic CSV adapter, driven by a column map.

Most bank exports are the same shape wearing different column names: a date, a
description, and either one signed amount or a debit/credit pair. Rather than a
bespoke parser per bank, each source declares a `ColumnMap` and this module does
the work.

A new bank is therefore a dozen lines in `PROFILES` (or in the rules file under
`csv_profiles:`), not a new module.
"""

import csv
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from ..model import Leg, Txn, to_fraction


@dataclass
class ColumnMap:
    """How one bank's CSV columns map onto the normalised fields."""

    date: str
    description: str
    amount: Optional[str] = None          # single signed column
    debit: Optional[str] = None           # or a debit/credit pair
    credit: Optional[str] = None
    currency: Optional[str] = None        # column holding the currency
    fixed_currency: Optional[str] = None  # or a constant, when the file omits it
    fee: Optional[str] = None
    reference: Optional[str] = None
    counterparty: Optional[str] = None
    source_id: Optional[str] = None
    date_formats: List[str] = field(
        default_factory=lambda: ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"]
    )
    encoding: str = "utf-8-sig"
    delimiter: str = ","
    skip_rows: int = 0
    # True when a positive figure in the amount column means money leaving.
    invert: bool = False

    def parse_date(self, raw: str):
        raw = (raw or "").strip()[:10]
        for fmt in self.date_formats:
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
        raise ValueError("Unrecognised date %r — add its format to the column map" % raw)


def parse(path: str, colmap: ColumnMap, account: str, source: str) -> List[Txn]:
    """Read one CSV into normalised transactions against a single account."""
    out: List[Txn] = []

    with open(path, "r", encoding=colmap.encoding) as fh:
        for _ in range(colmap.skip_rows):
            next(fh, None)
        for row in csv.DictReader(fh, delimiter=colmap.delimiter):
            raw_date = row.get(colmap.date)
            if not raw_date:
                continue

            if colmap.amount:
                amount = to_fraction(row.get(colmap.amount))
            else:
                debit = to_fraction(row.get(colmap.debit)) if colmap.debit else 0
                credit = to_fraction(row.get(colmap.credit)) if colmap.credit else 0
                amount = credit - debit
            if colmap.invert:
                amount = -amount
            if amount == 0:
                continue

            currency = (
                row.get(colmap.currency) if colmap.currency else colmap.fixed_currency
            ) or colmap.fixed_currency
            counterparty = (row.get(colmap.counterparty) or "") if colmap.counterparty else ""
            description = (row.get(colmap.description) or "").strip() or counterparty

            txn = Txn(
                date=colmap.parse_date(raw_date),
                description=description,
                source=source,
                source_id=(row.get(colmap.source_id) or "") if colmap.source_id else "",
                reference=(row.get(colmap.reference) or "") if colmap.reference else "",
                counterparty=counterparty,
            )
            txn.legs.append(Leg(account, amount, currency))

            if colmap.fee:
                fee = to_fraction(row.get(colmap.fee))
                if fee:
                    txn.legs.append(Leg("Expenses:Bank Fees", fee, currency))
                    txn.legs[0].amount -= fee

            out.append(txn)

    return out


# Column maps per source.
#
# VERIFIED means the map was checked against a real export from that provider.
# PROVISIONAL means it is written from the provider's documented format but has
# not yet met a real file — check the column names on first run and correct them
# here or in the rules file rather than assuming they are right.
PROFILES: Dict[str, Dict] = {
    # PROVISIONAL — BBVA's Spanish export uses localised headers and dd/mm/yyyy.
    "bbva": {
        "colmap": ColumnMap(
            date="Fecha",
            description="Concepto",
            amount="Importe",
            fixed_currency="EUR",
            reference="Observaciones",
            date_formats=["%d/%m/%Y", "%Y-%m-%d"],
            encoding="latin-1",
        ),
        "account": "Assets:Current Assets:BBVA (EUR) ...1735",
        "status": "PROVISIONAL",
    },
    # PROVISIONAL — Upwork's Reports > Transaction History export.
    "upwork": {
        "colmap": ColumnMap(
            date="Date",
            description="Description",
            amount="Amount",
            fixed_currency="USD",
            reference="Ref ID",
            source_id="Ref ID",
            date_formats=["%b %d, %Y", "%Y-%m-%d"],
        ),
        "account": "Assets:Current Assets:Funds Upwork (USD)",
        "status": "PROVISIONAL",
    },
    # PROVISIONAL — Stripe's Balance transactions export.
    "stripe": {
        "colmap": ColumnMap(
            date="Created (UTC)",
            description="Description",
            amount="Gross",
            fee="Fee",
            currency="Currency",
            source_id="id",
            date_formats=["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"],
        ),
        "account": "Assets:Current Assets:Stripe:Stripe (EUR)",
        "status": "PROVISIONAL",
    },
}


def profile(name: str, rules=None) -> Dict:
    """Fetch a source profile, letting the rules file override any field."""
    if name not in PROFILES:
        raise SystemExit(
            "Unknown CSV source %r. Known: %s" % (name, ", ".join(sorted(PROFILES)))
        )
    spec = dict(PROFILES[name])
    overrides = ((rules.spec.get("csv_profiles") or {}).get(name) or {}) if rules else {}
    if "account" in overrides:
        spec["account"] = overrides["account"]
    if "columns" in overrides:
        base = spec["colmap"].__dict__.copy()
        base.update(overrides["columns"])
        spec["colmap"] = ColumnMap(**base)
        spec["status"] = "OVERRIDDEN"
    return spec
