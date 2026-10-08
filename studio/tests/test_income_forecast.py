import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))

import income_forecast as inc

TODAY = dt.date(2026, 10, 8)
FX = {"USD": 0.9, "GBP": 1.2}
AR_USD = "Root Account:Assets:Future Assets:Accounts Receivable:Accounts Receivable (USD)"
AR_EUR = "Root Account:Assets:Future Assets:Accounts Receivable:Accounts Receivable (EUR)"


def ar(date, qty, desc, path=AR_USD, cur="USD"):
    # val deliberately differs from qty: AR must be read in the leaf's own currency.
    return {"date": date, "desc": desc, "path": path, "cur": cur, "qty": qty, "val": qty * 0.9}


def test_paid_invoices_are_not_receivable():
    rows = [ar("2026-08-31", 1000, "KF Invoice"), ar("2026-09-01", -1000, "KHYENTSE")]
    assert inc.open_receivables(rows) == []


def test_payment_sorted_before_same_day_invoice_still_clears_it():
    rows = [ar("2026-04-02", -1000, "Khyentse"), ar("2026-04-02", 1000, "Khyentse")]
    assert inc.open_receivables(rows) == []


def test_part_paid_invoice_keeps_remainder_open():
    rows = [ar("2026-09-24", 34.45, "Invoice 890", AR_EUR, "EUR"), ar("2026-09-28", -30, "Invoice 890", AR_EUR, "EUR")]
    [item] = inc.open_receivables(rows)
    assert round(item["open"], 2) == 4.45


def test_receivable_lands_after_lag_in_mapped_account():
    rows = [ar("2026-10-07", 1000, "Harvest invoice 897 - TECHSTYLE", AR_EUR, "EUR")]
    cfg = {"receivables": {"clients": [{"match": "techstyle", "account": "Wise Business (EUR)", "lag_days": 7}]}}
    [e] = inc.forecast_income(rows, TODAY, FX, cfg)
    assert (e["date"], e["tier"], e["account"], e["amount"]) == ("2026-10-14", "receivable", "Wise Business (EUR)", 1000)


def test_overdue_receivable_is_expected_tomorrow_and_unmatched_is_unknown():
    rows = [ar("2026-05-01", 100, "Someone new")]
    [e] = inc.forecast_income(rows, TODAY, FX, {})
    assert (e["date"], e["account"], e["amount"]) == ("2026-10-09", "Unknown", 90.0)


def test_recurring_respects_start_and_converts_currency():
    cfg = {"recurring": [{"label": "KF", "tier": "fixed", "cadence": "monthly", "day": 3,
                          "amount": 1000, "currency": "USD", "account": "Wise Business (USD)",
                          "start": "2026-11-03"}]}
    entries = inc.forecast_income([], TODAY, FX, cfg)
    assert entries[0]["date"] == "2026-11-03"
    assert entries[0]["amount"] == 900.0
    assert all(e["tier"] == "fixed" for e in entries)


def test_weekly_lands_on_weekday():
    cfg = {"recurring": [{"label": "NORE", "tier": "predicted", "cadence": "weekly", "weekday": 4,
                          "amount": 324, "currency": "USD", "account": "Wise Business (USD)"}]}
    dates = [e["date"] for e in inc.forecast_income([], TODAY, FX, cfg)[:2]]
    assert dates == ["2026-10-09", "2026-10-16"]


def test_past_milestones_are_dropped():
    cfg = {"milestones": [
        {"label": "old", "date": "2026-09-01", "amount": 1, "currency": "EUR", "account": "x"},
        {"label": "m2", "date": "2026-11-22", "amount": 850, "currency": "EUR", "account": "x"},
    ]}
    assert [e["label"] for e in inc.forecast_income([], TODAY, FX, cfg)] == ["m2"]


KF_CFG = {
    "receivables": {"clients": [{"match": r"khyentse|\bKF\b", "account": "Wise Business (USD)", "lag_days": 3}]},
    "recurring": [{"label": "KF", "match": r"khyentse|\bKF\b", "tier": "fixed", "cadence": "monthly", "day": 3,
                   "amount": 1000, "currency": "USD", "account": "Wise Business (USD)"}],
}


def test_invoiced_recurring_period_is_counted_once():
    # 31 Oct: October's KF invoice is booked to AR before its 3 Nov receipt.
    today = dt.date(2026, 11, 1)
    rows = [ar("2026-10-31", 1000, "KF Invoice")]
    nov = [e for e in inc.forecast_income(rows, today, FX, KF_CFG) if e["date"] <= "2026-11-30"]
    assert [(e["tier"], e["date"]) for e in nov] == [("receivable", "2026-11-03")]


def test_paid_invoice_still_suppresses_its_recurring_occurrence():
    # Paid early on 2 Nov: no receivable, and the 3 Nov occurrence must not reappear.
    today = dt.date(2026, 11, 2)
    rows = [ar("2026-10-31", 1000, "Invoice 893 - Khyentse Foundation"), ar("2026-11-02", -1000, "KHYENTSE")]
    entries = inc.forecast_income(rows, today, FX, KF_CFG)
    assert entries[0]["date"] == "2026-12-03"


def test_fixed_recurring_ignores_other_invoices_from_same_client():
    cfg = {"recurring": [{"label": "TS retainer", "match": "techstyle", "tier": "fixed", "cadence": "monthly",
                          "day": 10, "amount": 135, "currency": "EUR", "account": "Wise Business (EUR)"}]}
    rows = [ar("2026-11-03", 850, "TECHSTYLE milestone", AR_EUR, "EUR")]
    entries = inc.forecast_income(rows, TODAY, FX, cfg)
    assert any(e["tier"] == "fixed" and e["date"] == "2026-11-10" for e in entries)


def test_invoiced_milestone_drops_out():
    cfg = {"milestones": [{"label": "m2", "match": "techstyle", "date": "2026-11-22", "amount": 850,
                           "currency": "EUR", "account": "Wise Business (EUR)"}]}
    rows = [ar("2026-11-12", 850, "Harvest invoice 899 - TECHSTYLE", AR_EUR, "EUR")]
    assert [e["tier"] for e in inc.forecast_income(rows, TODAY, FX, cfg)] == ["receivable"]


def test_missing_config_is_an_error(tmp_path):
    import pytest
    with pytest.raises(RuntimeError):
        inc.load_config(tmp_path)


def test_base_tiers():
    assert inc.is_base({"type": "income", "tier": "receivable"})
    assert inc.is_base({"type": "income"})
    assert not inc.is_base({"type": "income", "tier": "predicted"})
    assert not inc.is_base({"type": "fixed"})


UNBILLED_CFG = {
    "receivables": {"clients": [
        {"match": "techstyle.*upwork", "account": "Wise Business (USD)", "lag_days": 10, "fee_pct": 10},
        {"match": "middle way", "account": "Wise Business (USD)", "lag_days": 10},
    ]},
    "unbilled": {"exclude": ["Maintenance Retainer"]},
}


def project(client, name, amt, cur="USD", fixed=False, billable=True):
    return {"client": client, "name": name, "uninvoiced_amt": amt, "uninvoiced_hrs": 1,
            "client_currency": cur, "is_fixed_fee": fixed, "is_billable": billable}


def test_unbilled_hours_are_invoiced_at_month_end_then_paid_after_lag():
    [e] = inc.forecast_income([], TODAY, FX, UNBILLED_CFG, [project("Middle Way Education (MWE)", "Framework", 1038.6)])
    assert (e["tier"], e["date"], e["account"], e["amount"]) == ("unbilled", "2026-11-10", "Wise Business (USD)", 934.74)


def test_unbilled_skips_fixed_fee_non_billable_excluded_and_zero():
    projects = [
        project("Techstyle", "Compliance Center", 2950, "EUR", fixed=True),
        project("X", "Admin", 50, billable=False),
        project("TECHSTYLE Accessories B.V.", "Techstyle Maintenance Retainer", 90, "EUR"),
        project("MWE", "Done", 0),
    ]
    assert inc.forecast_income([], TODAY, FX, UNBILLED_CFG, projects) == []


def test_unbilled_upwork_hours_net_of_fee():
    [e] = inc.forecast_income([], TODAY, FX, UNBILLED_CFG, [project("TECHSTYLE Accessories B.V.", "Techstyle Upwork (hourly)", 100)])
    assert e["amount"] == 81.0   # $100 less 10% fee, at 0.9


def test_unbilled_is_base_case():
    assert inc.is_base({"type": "income", "tier": "unbilled"})


def test_harvest_failure_is_missing_not_zero():
    assert inc.harvest_projects({"error": "401"}) is None
    assert inc.harvest_projects({"projects": [], "uninvoiced": {"error": "timeout"}}) is None
    assert inc.harvest_projects({"projects": [1], "uninvoiced": {}}) == [1]

