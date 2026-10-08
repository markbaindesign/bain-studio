"""Per-account cash flow projection: running balance per bank account from upcoming
bills and forecast income, with predicted top-up transfers into BBVA.

Shared by the daily Slack forecast (studio/scripts/account_forecast_report.py) and the
dashboard's Cashflow screen, so both always show the same numbers.
"""

from collections import defaultdict
from datetime import datetime

from income_forecast import BASE_TIERS

# upcoming_all `account` labels -> matching bank_balances name (substring match)
# Every billing_account value used in FINANCE_CONFIG_DIR/recurring-transactions.yaml
# must have an entry here, or its transactions fall through to "Unassigned (no account
# attributed)" in the Slack report instead of being forecast against a balance.
ACCOUNT_LABEL_MAP = {
    "BBVA EUR": "BBVA",
    "Wise Business (USD)": "Wise (Business):Wise Business (USD)",
    "Wise Business (GBP)": "Wise (Business):Wise Business (GBP)",
    "Wise Business (EUR)": "Wise (Business):Wise Business (EUR)",
    "Wise Main (USD)": "Wise (Personal):Wise Main (USD)",
    "Wise Main (GBP)": "Wise (Personal):Wise Main (GBP)",
}

# If the BBVA EUR balance would go negative, assume a top-up transfer lands from this
# account the same day, sized to exactly cover the deficit. Predicted, not scheduled —
# Mark moves this manually; the forecast just shows what it would take and when.
TRANSFER_SOURCE = "Wise Business (USD)"
TRANSFER_TARGET = "BBVA EUR"
EPS = 0.01


def _bank_name(balances, label):
    match = ACCOUNT_LABEL_MAP.get(label)
    return next((n for n in balances if match and match in n), None)


def build_forecast(data, window_end, income_tiers=None):
    """Income entries outside `income_tiers` are left out (None keeps every tier).
    Untiered income, e.g. hand-dated expected_income.yaml entries, always counts."""
    balances = {b["name"]: b["eur"] for b in data["bank_balances"] if b.get("liquid")}
    upcoming = [
        t for t in data.get("upcoming_all", [])
        if income_tiers is None or t.get("type") != "income"
        or t.get("tier") is None or t["tier"] in income_tiers
    ]

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
                    "type": "income", "tier": "transfer", "_priority": 0,
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
                rows.append((t["date"], t["label"], t.get("tier") or t.get("type", ""), delta, running, went_negative))

        if first_negative:
            shortfalls.append((short_name, *first_negative))
        if rows:
            tables.append((short_name, balances[bank_name], rows))

    return shortfalls, tables, unassigned
