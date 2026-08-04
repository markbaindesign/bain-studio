"""
Account forecast report — sends a daily Slack summary of upcoming payments
per bank account, flagging any that go negative.

Reads FINANCE_DATA_DIR/accounts.json (kept fresh by the gnucash_collector
cron job, which runs earlier in the morning). Does not refresh it itself.

Run: python3 studio/scripts/account_forecast_report.py
"""

import calendar
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent))
from notifier import notify


def _require_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} must be set in studio/.env -- no hardcoded fallback")
    return value


FINANCE_DATA_DIR = Path(_require_env("FINANCE_DATA_DIR"))
ACCOUNTS_FILE = FINANCE_DATA_DIR / "accounts.json"
WINDOW_DAYS = 21

# upcoming_all `account` labels -> matching bank_balances name (substring match)
ACCOUNT_LABEL_MAP = {
    "BBVA EUR": "BBVA",
    "Wise Business (USD)": "Wise (Business):Wise Business (USD)",
    "Wise Business (GBP)": "Wise (Business):Wise Business (GBP)",
    "Wise Main (USD)": "Wise (Personal):Wise Main (USD)",
    "Wise Main (GBP)": "Wise (Personal):Wise Main (GBP)",
}

# Known recurring incoming payments, confirmed by Mark 2026-07-27. Not derived from
# expected_income.yaml (that's for one-off manually dated entries) or from
# gnucash_parser.py's UPCOMING_PATTERNS (bills only, keyword-matched against ledger
# history) — this report projects its own recurring income forward so the daily Slack
# forecast doesn't go stale as manually-dated entries run out.
RECURRING_INCOME = [
    {
        "label": "Khyentse Foundation",
        "cadence": "monthly",   # lands on the last calendar day of the month
        "amount": 1000.0,
        "currency": "USD",
        "account": "Wise Business (USD)",
    },
    {
        "label": "Upwork - WordPress Technical Assistant",
        "cadence": "weekly",
        "weekday": 4,  # Friday (0=Monday); matches 2026-07-03/10/17 payment history
        "amount": 360.0,
        "currency": "USD",
        "account": "Wise Business (USD)",
    },
]
INCOME_HORIZON_DAYS = 400


def generate_recurring_income(today, fx):
    end = today + timedelta(days=INCOME_HORIZON_DAYS)
    entries = []
    for pattern in RECURRING_INCOME:
        rate = 1.0 if pattern["currency"] == "EUR" else fx.get(f"{pattern['currency']}_TO_EUR")
        if not rate:
            continue
        eur_amount = round(pattern["amount"] * rate, 2)

        occurrences = []
        if pattern["cadence"] == "monthly":
            d = today.replace(day=1)
            while d <= end:
                last_day = calendar.monthrange(d.year, d.month)[1]
                occ = date(d.year, d.month, last_day)
                if occ >= today:
                    occurrences.append(occ)
                d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
        elif pattern["cadence"] == "weekly":
            days_ahead = (pattern["weekday"] - today.weekday()) % 7
            occ = today + timedelta(days=days_ahead)
            while occ <= end:
                occurrences.append(occ)
                occ += timedelta(days=7)

        for occ in occurrences:
            entries.append({
                "label": pattern["label"],
                "date": str(occ),
                "amount": eur_amount,
                "currency": "EUR",
                "type": "income",
                "account": pattern["account"],
                "days": (occ - today).days,
            })
    return entries


# If the BBVA EUR balance would go negative, assume a top-up transfer lands from this
# account the same day, sized to exactly cover the deficit. Predicted, not scheduled —
# Mark moves this manually; the forecast just shows what it would take and when.
TRANSFER_SOURCE = "Wise Business (USD)"
TRANSFER_TARGET = "BBVA EUR"
EPS = 0.01


def _bank_name(balances, label):
    match = ACCOUNT_LABEL_MAP.get(label)
    return next((n for n in balances if match and match in n), None)


def build_forecast(data, window_end):
    balances = {b["name"]: b["eur"] for b in data["bank_balances"] if b.get("liquid")}
    upcoming = data.get("upcoming_all", [])

    by_account = defaultdict(list)
    unassigned = []
    for txn in upcoming:
        label = txn.get("account", "Unknown")
        if label == "Unknown":
            unassigned.append(txn)
            continue
        bank_name = _bank_name(balances, label)
        if not bank_name:
            unassigned.append(txn)
            continue
        by_account[bank_name].append(txn)

    # --- Predicted transfers: auto-cover any BBVA shortfall from Wise Business (USD) ---
    target_name = _bank_name(balances, TRANSFER_TARGET)
    source_name = _bank_name(balances, TRANSFER_SOURCE)
    if target_name and source_name:
        running = balances[target_name]
        for t in sorted(by_account.get(target_name, []), key=lambda t: t["date"]):
            delta = t["amount"] if t.get("type") == "income" else -t["amount"]
            prospective = running + delta
            if prospective < -EPS:
                deficit = round(-prospective, 2)
                by_account[source_name].append({
                    "label": "Predicted transfer to BBVA",
                    "date": t["date"], "amount": deficit,
                    "type": "transfer", "_priority": 0,
                })
                by_account[target_name].append({
                    "label": "Predicted transfer from Wise",
                    "date": t["date"], "amount": deficit,
                    "type": "income", "_priority": 0,
                })
                running += deficit
            running += delta

    shortfalls = []
    tables = []
    for bank_name, txns in by_account.items():
        running = balances[bank_name]
        txns_sorted = sorted(txns, key=lambda t: (t["date"], t.get("_priority", 1)))
        short_name = bank_name.replace("Current Assets:", "")

        rows = []
        first_negative = None
        for t in txns_sorted:
            delta = t["amount"] if t.get("type") == "income" else -t["amount"]
            running += delta
            went_negative = running < -EPS and first_negative is None
            if went_negative:
                first_negative = (t["date"], t["label"], running)
            txn_date = datetime.strptime(t["date"], "%Y-%m-%d").date()
            if txn_date <= window_end:
                rows.append((t["date"], t["label"], t.get("type", ""), delta, running, went_negative))

        if first_negative:
            shortfalls.append((short_name, *first_negative))
        if rows:
            tables.append((short_name, balances[bank_name], rows))

    return shortfalls, tables, unassigned


def format_table(name, start_balance, rows):
    lines = [f"{name}  (start €{start_balance:,.2f})"]
    lines.append(f"{'Date':<10} {'Label':<28} {'Type':<6} {'Amount':>11} {'Balance':>13}")
    for txn_date, label, txn_type, delta, running, flag in rows:
        amount_str = f"{delta:+,.2f}"
        balance_str = f"{running:,.2f}"
        flag_str = "  ⚠ SHORTFALL" if flag else ""
        lines.append(f"{txn_date:<10} {label[:28]:<28} {txn_type:<6} {amount_str:>11} {balance_str:>13}{flag_str}")
    return "\n".join(lines)


def main():
    if not ACCOUNTS_FILE.exists():
        notify(
            "Account forecast report failed — accounts.json not found",
            priority="high", sender="financial-review",
        )
        sys.exit(1)

    today = date.today()
    window_end = today + timedelta(days=WINDOW_DAYS)

    data = json.loads(ACCOUNTS_FILE.read_text())
    income_entries = generate_recurring_income(today, data.get("fx", {}))
    data["upcoming_all"] = data.get("upcoming_all", []) + income_entries
    shortfalls, tables, unassigned = build_forecast(data, window_end)

    if shortfalls:
        summary = "; ".join(f"{name} short €{abs(bal):,.2f} from {d} ({label})" for name, d, label, bal in shortfalls)
        message = f"⚠ Upcoming payments (next {WINDOW_DAYS}d): {summary}"
        priority = "high"
    else:
        message = f"Upcoming payments (next {WINDOW_DAYS}d) — all accounts projected to stay positive."
        priority = "normal"

    details = "\n\n".join(format_table(name, start, rows) for name, start, rows in tables)
    if unassigned:
        unassigned_in_window = [
            t for t in unassigned
            if datetime.strptime(t["date"], "%Y-%m-%d").date() <= window_end
        ]
        if unassigned_in_window:
            details += "\n\nUnassigned (no account attributed):\n"
            details += "\n".join(f"{t['date']}  {t['label']}  €{t['amount']:,.2f}" for t in unassigned_in_window)

    notify(
        message,
        subject=f"Daily payment forecast — next {WINDOW_DAYS} days",
        priority=priority,
        sender="financial-review",
        details=details,
    )


if __name__ == "__main__":
    main()
