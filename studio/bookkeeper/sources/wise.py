"""Wise adapter — reads either the API statement or a downloaded CSV.

Both routes produce the same column set, so one parser serves both.

Fee semantics, verified against the studio's own data and consistent with
playbook section 3: Wise reports `Source amount (after fees)` net of its
charge, and the actual movement on the balance is that figure *plus*
`Source fee amount`. A $1,000 inbound transfer with a $6.11 fee appears as
993.89, and 993.89 + 6.11 = 1000.00.

Card transactions billed in another currency are booked at the amount that
left the balance, in the balance's own currency — the merchant-currency figure
is informational and does not need a currency crossing.
"""

import csv
import io
import json
import os
import subprocess
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from ..model import Leg, Txn, to_fraction

WISE_CLIENT = os.path.expanduser("~/.config/wise/wise_client.py")

# Profile/currency to account path. Overridable from the rules file so the
# mapping is not baked into a public repo.
DEFAULT_ACCOUNTS = {
    ("business", "USD"): "Assets:Current Assets:Wise:Wise (Business):Wise Business (USD)",
    ("business", "GBP"): "Assets:Current Assets:Wise:Wise (Business):Wise Business (GBP)",
    ("business", "EUR"): "Assets:Current Assets:Wise:Wise (Business):Wise Business (EUR)",
    ("personal", "USD"): "Assets:Current Assets:Wise:Wise (Personal):Wise Main (USD)",
    ("personal", "GBP"): "Assets:Current Assets:Wise:Wise (Personal):Wise Main (GBP)",
    ("personal", "EUR"): "Assets:Current Assets:Wise:Wise (Personal):Wise Main (EUR)",
}

# From the wise-pulse skill, which already documents these.
BALANCES = {
    ("business", "USD"): ("55828700", "93635981"),
    ("business", "GBP"): ("55828700", "93635748"),
    ("business", "EUR"): ("55828700", "93635923"),
    ("personal", "USD"): ("2753862", "18115479"),
    ("personal", "GBP"): ("2753862", "32845501"),
    ("personal", "EUR"): ("2753862", "18115478"),
}


def _date(row: Dict) -> Optional[datetime.date]:
    raw = (row.get("Finished on") or row.get("Created on") or "").strip()
    if not raw:
        return None
    return datetime.strptime(raw[:10], "%Y-%m-%d").date()


def _profile_of(row: Dict, default: str) -> str:
    """Which Wise profile's balance actually moved.

    A statement belongs to exactly one profile, so `default` — the profile the
    caller asked for — is the answer, and is trusted outright.

    Only when the caller did not say do we infer, and then from the *holder*
    side of the row rather than from either name appearing anywhere: on a
    payment out the holder is the source, on one in it is the target. Matching
    on either name is wrong for a transfer between the two profiles, where both
    names are present on every such row — it sent money leaving the personal
    account into the business account instead.
    """
    if default:
        return default
    holder = (
        row.get("Source name") if (row.get("Direction") or "").upper() != "IN"
        else row.get("Target name")
    ) or ""
    return "business" if "bain design" in holder.lower() else "personal"


def parse_rows(
    rows: Iterable[Dict],
    accounts: Dict,
    default_profile: str = "",
    skip_zero: bool = True,
) -> List[Txn]:
    """Convert Wise statement rows into normalised transactions."""
    out: List[Txn] = []

    for row in rows:
        status = (row.get("Status") or "").upper()
        direction = (row.get("Direction") or "").upper()
        if status not in ("COMPLETED", "REFUNDED"):
            continue

        # Wise marks a reversed payment by setting the ORIGINAL row's status to
        # REFUNDED rather than adding a credit row. So an outgoing marked
        # REFUNDED never left the balance, and booking it invents an expense
        # that never happened — a duplicated Uber charge, a $1 card
        # verification, a failed payment that was retried two days later.
        #
        # Verified by reconciliation: skipping these lands all six Wise balances
        # on the cent against the live figures; booking them is out by exactly
        # the refunded amounts.
        if status == "REFUNDED" and direction == "OUT":
            continue

        day = _date(row)
        if day is None:
            continue

        src_ccy = (row.get("Source currency") or "").strip()
        tgt_ccy = (row.get("Target currency") or "").strip() or src_ccy
        src_amt = to_fraction(row.get("Source amount (after fees)"))
        tgt_amt = to_fraction(row.get("Target amount (after fees)"))
        fee = to_fraction(row.get("Source fee amount"))
        profile = _profile_of(row, default_profile)

        counterparty = (
            row.get("Target name") if direction == "OUT" else row.get("Source name")
        ) or ""
        description = counterparty or (row.get("Reference") or "").strip() or "Wise transaction"

        txn = Txn(
            date=day,
            description=description,
            source="wise",
            source_id=row.get("ID") or "",
            reference=(row.get("Reference") or "").strip(),
            counterparty=counterparty,
        )

        if direction == "IN":
            account = accounts.get((profile, tgt_ccy))
            if not account:
                continue
            if skip_zero and tgt_amt == 0:
                continue
            txn.legs.append(Leg(account, tgt_amt, tgt_ccy))
            if fee and (row.get("Source fee currency") or src_ccy) == tgt_ccy:
                txn.legs.append(Leg("Expenses:Bank Fees", fee, tgt_ccy))

        elif direction == "OUT":
            account = accounts.get((profile, src_ccy))
            if not account:
                continue
            gross = src_amt + fee
            if skip_zero and gross == 0:
                # A card authorisation hold, not a movement.
                continue
            txn.legs.append(Leg(account, -gross, src_ccy))
            if fee:
                txn.legs.append(Leg("Expenses:Bank Fees", fee, src_ccy))

        else:  # NEUTRAL — a conversion between two of your own balances
            src_account = accounts.get((profile, src_ccy))
            tgt_account = accounts.get((profile, tgt_ccy))
            if not src_account or not tgt_account or src_ccy == tgt_ccy:
                continue
            gross = src_amt + fee
            if skip_zero and gross == 0:
                continue
            txn.description = "Convert %s to %s" % (src_ccy, tgt_ccy)
            txn.legs.append(Leg(src_account, -gross, src_ccy))
            if fee:
                txn.legs.append(Leg("Expenses:Bank Fees", fee, src_ccy))
            # The destination leg's value is the converted amount expressed in
            # the transaction currency — the amount actually converted, which
            # excludes the fee (playbook section 3).
            txn.legs.append(Leg(tgt_account, tgt_amt, tgt_ccy, value=src_amt))
            txn.balanced_by_construction = True

        if status == "REFUNDED" and direction == "IN":
            # A refund arriving is real money, but no inbound REFUNDED row fell
            # inside the window the balance reconciliation covered, so this
            # direction is unproven. Import it, but never silently.
            txn.needs_review = True
            txn.review_reason = (
                "Inbound row marked REFUNDED — confirm this is a refund received "
                "rather than an incoming payment that was reversed"
            )

        if txn.legs:
            out.append(txn)

    return out


def from_csv(path: str, accounts: Dict, default_profile: str = "") -> List[Txn]:
    with open(path, "r", encoding="utf-8-sig") as fh:
        return parse_rows(list(csv.DictReader(fh)), accounts, default_profile)


def from_api(
    profile: str, currency: str, start: str, end: str, accounts: Dict
) -> List[Txn]:
    """Pull a per-balance statement straight from the Wise API.

    Uses the existing client at ~/.config/wise/wise_client.py, the same one
    wise-pulse uses, so credentials are already in place.
    """
    if not os.path.exists(WISE_CLIENT):
        raise SystemExit(
            "Wise API client not found at %s. See the wise-pulse skill for setup."
            % WISE_CLIENT
        )
    key = (profile, currency)
    if key not in BALANCES:
        raise SystemExit("Unknown Wise balance: %s %s" % (profile, currency))
    profile_id, balance_id = BALANCES[key]

    result = subprocess.run(
        ["python3", WISE_CLIENT, "statement", profile_id, balance_id,
         currency, start, end],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise SystemExit(
            "Wise API call failed for %s %s: %s"
            % (profile, currency, result.stderr.strip())
        )

    payload = result.stdout.strip()
    # The client returns JSON; a CSV statement is also accepted so the adapter
    # keeps working if the endpoint's format is switched.
    if payload.startswith("{") or payload.startswith("["):
        return _from_api_json(json.loads(payload), profile, currency, accounts)
    return parse_rows(list(csv.DictReader(io.StringIO(payload))), accounts, profile)


def _from_api_json(payload, profile: str, currency: str, accounts: Dict) -> List[Txn]:
    """Convert Wise's JSON statement into the same shape as the CSV export."""
    transactions = payload.get("transactions", payload) if isinstance(payload, dict) else payload
    rows = []
    for item in transactions:
        amount = item.get("amount", {}) or {}
        fee = item.get("totalFees", {}) or {}
        details = item.get("details", {}) or {}
        value = to_fraction(amount.get("value", 0))
        inbound = value > 0
        rows.append({
            "ID": item.get("referenceNumber", ""),
            "Status": "COMPLETED",
            "Direction": "IN" if inbound else "OUT",
            "Created on": (item.get("date") or "")[:10],
            "Finished on": (item.get("date") or "")[:10],
            "Source fee amount": str(abs(to_fraction(fee.get("value", 0)))),
            "Source fee currency": fee.get("currency", currency),
            "Source name": details.get("senderName", "") if inbound else "",
            "Source amount (after fees)": str(abs(value)),
            "Source currency": amount.get("currency", currency),
            "Target name": details.get("merchant", {}).get("name", "")
            if isinstance(details.get("merchant"), dict)
            else details.get("recipient", ""),
            "Target amount (after fees)": str(abs(value)),
            "Target currency": amount.get("currency", currency),
            "Reference": details.get("paymentReference", "") or details.get("description", ""),
        })
    return parse_rows(rows, accounts, profile)


def account_map(rules) -> Dict:
    """Merge any account overrides from the rules file over the defaults."""
    mapping = dict(DEFAULT_ACCOUNTS)
    for key, path in (rules.spec.get("wise_accounts") or {}).items():
        profile, _, currency = key.partition(".")
        mapping[(profile.strip(), currency.strip().upper())] = path
    return mapping
