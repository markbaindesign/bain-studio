"""
upwork_check.py — Flag Upwork clients with earnings in a quarter but no Harvest invoice.

Every Upwork client gets a Harvest invoice each quarter (invoices 874, 875, 886, 893,
894 ...), so the gestor has a sales invoice behind each Upwork payment. This reads an
Upwork transaction report CSV (Reports > Transaction History > Download CSV) and lists
clients paid in the quarter that have no Harvest invoice issued in it.

Earnings are counted by payment date, as the CSV records them. Client names are matched
loosely ("TECHSTYLE" = "TECHSTYLE Accessories B.V."), so a flag is a prompt to check,
not proof that an invoice is missing.
"""

from __future__ import annotations

import csv
import re
from datetime import date, datetime
from pathlib import Path

EARNING_TYPES = {"Hourly", "Fixed-price", "Fixed Price", "Bonus"}
_SUFFIXES = {"bv", "b", "v", "ltd", "limited", "sl", "s", "l", "inc", "llc", "gmbh", "co"}


def find_report(search_dir: Path) -> Path | None:
    """Newest *_transaction_report.csv in search_dir (names start with an ISO date)."""
    reports = sorted(search_dir.glob("*_transaction_report.csv"))
    return reports[-1] if reports else None


def _norm(name: str) -> list[str]:
    words = re.sub(r"[^a-z0-9 ]", " ", name.lower()).split()
    return [w for w in words if w not in _SUFFIXES]


def same_client(upwork_name: str, harvest_name: str) -> bool:
    a, b = _norm(upwork_name), _norm(harvest_name)
    if not a or not b:
        return False
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    return longer[: len(shorter)] == shorter


def upwork_earnings(report: Path, start: date, end: date) -> tuple[dict, date | None]:
    """{client: (total_usd, first_paid, last_paid)} for earnings paid start..end,
    plus the latest date in the report (to spot a stale export)."""
    earnings: dict[str, list] = {}
    latest = None
    with report.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            try:
                paid = datetime.strptime(row["Date"], "%b %d, %Y").date()
            except (KeyError, ValueError):
                continue
            latest = paid if latest is None or paid > latest else latest
            if row.get("Transaction type") not in EARNING_TYPES or not start <= paid <= end:
                continue
            client = (row.get("Client team") or "").strip() or "unknown"
            e = earnings.setdefault(client, [0.0, paid, paid])
            e[0] += float(row.get("Amount $") or 0)
            e[1], e[2] = min(e[1], paid), max(e[2], paid)
    return {k: tuple(v) for k, v in earnings.items()}, latest


def uninvoiced(earnings: dict, harvest_clients: list[str]) -> dict:
    """Subset of earnings whose client matches no Harvest invoice client."""
    return {c: v for c, v in earnings.items()
            if not any(same_client(c, h) for h in harvest_clients)}


def report_check(report: Path | None, start: date, end: date, harvest_clients: list[str]) -> None:
    print(f"\nUpwork clients vs Harvest invoices")
    if report is None:
        print("  [ ] No Upwork transaction report found - download one (Reports > Transaction"
              " History > CSV) into the Financial folder and re-run")
        return
    earnings, latest = upwork_earnings(report, start, end)
    print(f"  Report: {report.name}")
    if latest and latest < end:
        print(f"  [!] Report ends {latest.isoformat()}, before quarter end - download a newer one")
    if not earnings:
        print("  No Upwork earnings in the quarter")
        return
    missing = uninvoiced(earnings, harvest_clients)
    for client, (total, first, last) in sorted(earnings.items()):
        mark = "[ ]" if client in missing else "[x]"
        note = "  <- no Harvest invoice this quarter" if client in missing else ""
        print(f"  {mark} {client}: ${total:,.2f} paid {first.isoformat()}..{last.isoformat()}{note}")
