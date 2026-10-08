"""
Account forecast report — sends a daily Slack summary of upcoming payments
per bank account, flagging any that go negative.

Reads FINANCE_DATA_DIR/accounts.json (kept fresh by the gnucash_collector
cron job, which runs earlier in the morning). Does not refresh it itself.

Run: python3 studio/scripts/account_forecast_report.py
"""

import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))
from notifier import notify
from cashflow import BASE_TIERS, build_forecast


def _require_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} must be set in studio/.env -- no hardcoded fallback")
    return value


FINANCE_DATA_DIR = Path(_require_env("FINANCE_DATA_DIR"))
ACCOUNTS_FILE = FINANCE_DATA_DIR / "accounts.json"
WINDOW_DAYS = 21

def format_table(name, start_balance, rows):
    lines = [f"{name}  (start €{start_balance:,.2f})"]
    lines.append(f"{'Date':<10} {'Label':<28} {'Type':<10} {'Amount':>11} {'Balance':>13}")
    for txn_date, label, txn_type, delta, running, flag in rows:
        amount_str = f"{delta:+,.2f}"
        balance_str = f"{running:,.2f}"
        flag_str = "  ⚠ SHORTFALL" if flag else ""
        lines.append(f"{txn_date:<10} {label[:28]:<28} {txn_type:<10} {amount_str:>11} {balance_str:>13}{flag_str}")
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
    if not any(t.get("type") == "income" for t in data.get("upcoming_all", [])):
        notify(
            "Account forecast not sent — accounts.json has no forecast income. "
            "Check FINANCE_CONFIG_DIR/income.yaml and Accounts Receivable.",
            priority="high", sender="financial-review",
        )
        sys.exit(1)

    # Shortfalls are judged on the base case (invoices sent + fixed recurring income).
    # Predicted income and milestones are reported as upside, not relied on.
    shortfalls, tables, unassigned = build_forecast(data, window_end, BASE_TIERS)
    with_upside, _, _ = build_forecast(data, window_end)
    upside_short = {name: bal for name, _, _, bal in with_upside}

    if shortfalls:
        def _upside(name):
            if name not in upside_short:
                return "covered if predicted income and milestones land"
            return f"still short €{abs(upside_short[name]):,.2f} even with predicted income"
        summary = "; ".join(
            f"{name} short €{abs(bal):,.2f} from {d} ({label}), {_upside(name)}"
            for name, d, label, bal in shortfalls
        )
        message = f"⚠ Upcoming payments (next {WINDOW_DAYS}d): {summary}"
        priority = "high"
    else:
        message = f"Upcoming payments (next {WINDOW_DAYS}d) — all accounts projected to stay positive."
        priority = "normal"

    details = "\n\n".join(format_table(name, start, rows) for name, start, rows in tables)
    missing = data.get("income_sources_missing") or []
    if missing:
        message += f" (income incomplete: {', '.join(missing)} unavailable)"
    if unassigned:
        unassigned_in_window = [
            t for t in unassigned
            if datetime.strptime(t["date"], "%Y-%m-%d").date() <= window_end
        ]
        if unassigned_in_window:
            details += "\n\nUnassigned (no matching account balance):\n"
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
