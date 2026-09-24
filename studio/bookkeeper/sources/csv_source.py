"""Generic tabular adapter for CSV and XLSX exports, driven by a column map.

Most bank exports are the same shape wearing different column names: a date, a
description, and either one signed amount or a debit/credit pair. Rather than a
bespoke parser per bank, each source declares a `ColumnMap` and this module does
the work.

A new bank is therefore a dozen lines in `PROFILES` (or in the rules file under
`csv_profiles:`), not a new module.
"""

import csv
import os
from dataclasses import dataclass, field
from datetime import date as date_cls, datetime
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
    # A second date column for the same movement (BBVA's value date). Dedupe
    # matches on either date; the main `date` is still the one that is booked.
    alt_date: Optional[str] = None
    date_formats: List[str] = field(
        default_factory=lambda: ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"]
    )
    encoding: str = "utf-8-sig"
    delimiter: str = ","
    skip_rows: int = 0
    # XLSX only: which sheet, and the 1-based row holding the column headers.
    sheet: Optional[str] = None
    header_row: int = 1
    # Skip a row whose named column is empty. Upwork lists scheduled earnings
    # with no balance yet; they have not happened and must not be booked.
    require: Optional[str] = None
    # Skip rows dated after today for the same reason.
    skip_future: bool = True
    # True when a positive figure in the amount column means money leaving.
    invert: bool = False

    def parse_date(self, raw):
        # openpyxl hands back real dates for some cells and strings for others.
        if isinstance(raw, datetime):
            return raw.date()
        if isinstance(raw, date_cls):
            return raw
        raw = (str(raw) if raw is not None else "").strip()
        # Try the whole string first. Truncating to 10 characters up front
        # would trim an ISO timestamp correctly but mangle "Sep 4, 2026".
        for candidate in (raw, raw[:10]):
            for fmt in self.date_formats:
                try:
                    return datetime.strptime(candidate, fmt).date()
                except ValueError:
                    continue
        raise ValueError("Unrecognised date %r — add its format to the column map" % raw)


def _read_rows(path: str, colmap: ColumnMap) -> List[Dict]:
    """Read a CSV or XLSX into a list of dicts keyed by column header."""
    if os.path.splitext(path)[1].lower() in (".xlsx", ".xlsm"):
        import openpyxl

        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        ws = wb[colmap.sheet] if colmap.sheet else wb.worksheets[0]
        rows = list(ws.iter_rows(values_only=True))
        header = ["" if c is None else str(c).strip()
                  for c in rows[colmap.header_row - 1]]
        out = []
        for raw in rows[colmap.header_row:]:
            out.append({h: v for h, v in zip(header, raw) if h})
        return out

    with open(path, "r", encoding=colmap.encoding) as fh:
        for _ in range(colmap.skip_rows):
            next(fh, None)
        return list(csv.DictReader(fh, delimiter=colmap.delimiter))


def _joined(row: Dict, spec) -> str:
    """A column name, or several joined — lets rules see more than one field."""
    if not spec:
        return ""
    cols = spec if isinstance(spec, (list, tuple)) else [spec]
    return " ".join(str(row.get(c)).strip() for c in cols
                    if row.get(c) not in (None, ""))


def parse(path: str, colmap: ColumnMap, account: str, source: str) -> List[Txn]:
    """Read one export into normalised transactions against a single account."""
    out: List[Txn] = []
    today = datetime.now().date()

    if True:
        for row in _read_rows(path, colmap):
            raw_date = row.get(colmap.date)
            if raw_date in (None, ""):
                continue
            if colmap.require and row.get(colmap.require) in (None, ""):
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
            counterparty = _joined(row, colmap.counterparty)
            description = _joined(row, colmap.description) or counterparty

            day = colmap.parse_date(raw_date)
            if colmap.skip_future and day > today:
                # Scheduled, not settled. Booking it invents income.
                continue

            txn = Txn(
                date=day,
                description=description,
                source=source,
                source_id=(str(row.get(colmap.source_id) or "")
                           if colmap.source_id else ""),
                reference=_joined(row, colmap.reference),
                counterparty=counterparty,
            )
            txn.legs.append(Leg(account, amount, currency))

            raw_alt = row.get(colmap.alt_date) if colmap.alt_date else None
            if raw_alt not in (None, ""):
                try:
                    alt = colmap.parse_date(raw_alt)
                except ValueError:
                    alt = None
                if alt and alt != day:
                    txn.alt_dates.append(alt)

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
    # VERIFIED 2026-09-08 against a real "Últimos movimientos" export.
    # Sheet "Informe BBVA", headers on row 5, data from row 6, dd/mm/yyyy.
    # Two date columns: "Fecha" (posting) and "F.Valor" (value). Fecha is the
    # one the book uses — checked by matching both against existing entries,
    # 22 hits to 20.
    "bbva": {
        "colmap": ColumnMap(
            date="Fecha",
            description=["Concepto", "Movimiento"],
            amount="Importe",
            fixed_currency="EUR",
            reference="Observaciones",
            alt_date="F.Valor",
            date_formats=["%d/%m/%Y", "%Y-%m-%d"],
            sheet="Informe BBVA",
            header_row=5,
        ),
        "account": "Assets:Current Assets:BBVA (EUR) ...1735",
        "status": "VERIFIED",
    },
    # VERIFIED 2026-09-08 against a real Reports > Transactions export.
    # The type column carries the meaning — Hourly, Service Fee, Withdrawal,
    # Withdrawal Fee, Subscription — so it is joined into the reference where
    # the rules can see it.
    #
    # Upwork lists scheduled earnings with a future date and no running
    # balance. Those have not happened; `require` and `skip_future` drop them.
    "upwork": {
        "colmap": ColumnMap(
            date="Date",
            description=["Transaction summary"],
            amount="Amount $",
            fixed_currency="USD",
            reference=["Transaction type", "Transaction summary details"],
            source_id="Ref ID",
            date_formats=["%b %d, %Y", "%Y-%m-%d"],
            require="Current balance $",
        ),
        "account": "Assets:Current Assets:Funds Upwork (USD)",
        "status": "VERIFIED",
    },
    # PROVISIONAL — Stripe's Balance transactions export, not yet seen.
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
