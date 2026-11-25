"""
Harvest KF collector — writes a time-budget snapshot for the KF-WEB
retainer to context/projects/kf/time_snapshot.json.

Run: python3 studio/collectors/harvest_kf_collector.py
"""

import json
import sys
from datetime import datetime, timezone, date
from pathlib import Path

import requests
import yaml

import os
from dotenv import load_dotenv as _load_dotenv
_load_dotenv(Path(__file__).parent.parent / ".env")

ROOT         = Path(__file__).parents[2]
CONTENT_DIR  = Path(os.getenv("STUDIO_CONTENT_DIR", ROOT / "context"))
BUDGET_FILE  = CONTENT_DIR / 'projects' / 'kf' / 'budget.yaml'
OUTPUT_FILE  = CONTENT_DIR / 'projects' / 'kf' / 'time_snapshot.json'
ENV_FILE    = ROOT / 'studio' / '.env'

BASE = 'https://api.harvestapp.com/api/v2'


def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, _, v = line.partition('=')
                env[k.strip()] = v.strip()
    return env


def harvest_get(path, params, headers):
    r = requests.get(f'{BASE}{path}', headers=headers, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def fetch_year_hours(project_id, year, headers):
    from_date = f'{year}-01-01'
    to_date   = f'{year}-12-31'
    total     = 0.0
    by_month  = {}
    page      = 1

    while True:
        data = harvest_get(
            '/time_entries',
            {'project_id': project_id, 'from': from_date, 'to': to_date,
             'per_page': 100, 'page': page},
            headers,
        )
        for entry in data.get('time_entries', []):
            hours     = entry.get('hours', 0) or 0
            spent_at  = entry.get('spent_date', '')
            month_key = spent_at[:7] if spent_at else 'unknown'
            total += hours
            by_month[month_key] = by_month.get(month_key, 0.0) + hours

        if data.get('next_page'):
            page += 1
        else:
            break

    return round(total, 2), {k: round(v, 2) for k, v in sorted(by_month.items())}


def calc_carry_over(prev_cfg, headers):
    """Return (carry_over_hours, prev_logged, prev_target).
    carry_over > 0 means hours owed this year; < 0 means credit.
    """
    prev_monthly = prev_cfg['monthly_budget_usd'] / prev_cfg['hourly_rate_usd']
    prev_annual  = prev_monthly * 12
    prev_logged, _ = fetch_year_hours(prev_cfg['harvest_project_id'], prev_cfg['year'], headers)
    carry_over = round(prev_annual - prev_logged, 2)  # positive = short = owed
    return carry_over, round(prev_logged, 2), round(prev_annual, 2)


def build_snapshot(budget, env):
    monthly_hours = budget['monthly_budget_usd'] / budget['hourly_rate_usd']
    annual_hours  = monthly_hours * 12
    year          = budget['year']
    project_id    = budget['harvest_project_id']

    headers = {
        'Authorization':      f"Bearer {env['HARVEST_TOKEN']}",
        'Harvest-Account-Id': str(env['HARVEST_ACCOUNT_ID']),
        'User-Agent':         'BainDesign-Collector/1.0',
    }

    year_hours, by_month = fetch_year_hours(project_id, year, headers)

    # Carry-over from previous year
    carry_over = 0.0
    prev_logged = None
    prev_target = None
    prev_year   = None
    if 'previous_year' in budget:
        carry_over, prev_logged, prev_target = calc_carry_over(budget['previous_year'], headers)
        prev_year = budget['previous_year']['year']

    # Adjusted annual target = base + carry-over owed (or minus credit)
    adjusted_annual = round(annual_hours + carry_over, 2)

    today          = date.today()
    current_month  = today.strftime('%Y-%m')
    months_elapsed = today.month  # 1–12

    # Paced monthly target: recalculated each month based on actual hours logged
    # in completed months vs what remains to reach the adjusted annual target.
    completed_hours = sum(v for k, v in by_month.items() if k < current_month)
    months_remaining = 13 - today.month  # months left including current (Dec=1, Jun=7)
    paced_monthly = (adjusted_annual - completed_hours) / months_remaining

    # Year target to date: completed actual + current-month paced target.
    # Earlier shortfalls are absorbed into the pacing, so year_variance always
    # equals month_variance — it is the current month's gap, not a cumulative one.
    year_target_to_date = round(completed_hours + paced_monthly, 2)
    year_variance       = round(year_hours - year_target_to_date, 2)

    month_hours    = by_month.get(current_month, 0.0)
    month_target   = round(paced_monthly, 2)
    month_variance = round(month_hours - month_target, 2)

    # The numbers that answer "how much do I still have to work?"
    year_hours_remaining  = round(max(adjusted_annual - year_hours, 0), 2)
    month_hours_remaining = round(max(paced_monthly - month_hours, 0), 2)

    # Days left in the current month, including today, for a daily pace
    next_month = date(today.year + today.month // 12, today.month % 12 + 1, 1)
    days_in_month   = (next_month - date(today.year, today.month, 1)).days
    month_days_left = days_in_month - today.day + 1
    month_daily_pace = round(month_hours_remaining / month_days_left, 2)

    # Where the month should be by today if worked evenly (for on/off-pace colouring)
    month_expected_by_today = round(paced_monthly * (today.day - 1) / days_in_month, 2)

    # True cumulative position at the start of this month against the base
    # retainer, including last year's carry-over. Positive = hours owed to KF.
    owed_at_month_start = round(
        (months_elapsed - 1) * monthly_hours + carry_over - completed_hours, 2)

    return {
        'generated_at':   datetime.now(timezone.utc).isoformat(),
        'project':        budget['client'],
        'harvest_project_id': project_id,
        'year':           year,
        'rate_usd':       budget['hourly_rate_usd'],
        'monthly_budget_usd':        budget['monthly_budget_usd'],
        'monthly_hours_target':      round(monthly_hours, 2),
        'annual_hours_target':       round(annual_hours, 2),
        'carry_over_hours':          carry_over,
        'carry_over_from_year':      prev_year,
        'prev_year_logged':          prev_logged,
        'prev_year_target':          prev_target,
        'adjusted_annual_target':    adjusted_annual,
        'paced_monthly_target':      round(paced_monthly, 2),
        'completed_hours':           round(completed_hours, 2),
        'months_remaining':          months_remaining,
        'year_hours_logged':         year_hours,
        'year_target_to_date':       year_target_to_date,
        'year_variance':             year_variance,
        'months_elapsed':            months_elapsed,
        'current_month':             current_month,
        'month_hours_logged':        month_hours,
        'month_hours_target':        month_target,
        'month_variance':            month_variance,
        'year_hours_remaining':      year_hours_remaining,
        'month_hours_remaining':     month_hours_remaining,
        'month_days_left':           month_days_left,
        'month_daily_pace':          month_daily_pace,
        'month_expected_by_today':   month_expected_by_today,
        'owed_at_month_start':       owed_at_month_start,
        'by_month':                  by_month,
    }


def print_status(snap):
    yr       = snap['year']
    co       = snap['carry_over_hours']
    m_name   = datetime.strptime(snap['current_month'], '%Y-%m').strftime('%b')
    owed     = snap['owed_at_month_start']

    print(f'KF {yr} — hours still to work')
    print(f'  This month ({m_name}): {snap["month_hours_remaining"]:5.1f}h   '
          f'({snap["month_hours_logged"]:.1f}h of {snap["month_hours_target"]:.1f}h logged; '
          f'{snap["month_days_left"]} days left ≈ {snap["month_daily_pace"]:.1f}h/day)')
    print(f'  This year:        {snap["year_hours_remaining"]:5.1f}h   '
          f'({snap["year_hours_logged"]:.1f}h of {snap["adjusted_annual_target"]:.1f}h logged)')
    print()
    print('How the targets are worked out')
    print(f'  Base retainer: {snap["monthly_hours_target"]:.2f}h/month '
          f'(${snap["monthly_budget_usd"]} at ${snap["rate_usd"]}/h), '
          f'{snap["annual_hours_target"]:.1f}h/year')
    if co != 0:
        co_dir = 'owed' if co > 0 else 'credit'
        print(f'  {snap["carry_over_from_year"]} carry-over: {abs(co):.1f}h {co_dir} '
              f'(logged {snap["prev_year_logged"]:.1f}h of {snap["prev_year_target"]:.1f}h) '
              f'→ {yr} target {snap["adjusted_annual_target"]:.1f}h')
    print(f'  Monthly target: ({snap["adjusted_annual_target"]:.1f}h − '
          f'{snap["completed_hours"]:.1f}h done before {m_name}) ÷ '
          f'{snap["months_remaining"]} months = {snap["paced_monthly_target"]:.1f}h')
    if owed > 0:
        print(f'  Catch-up owed at start of {m_name}: {owed:.1f}h behind the base retainer')
    else:
        print(f'  At start of {m_name}: {abs(owed):.1f}h ahead of the base retainer')


def main():
    env    = load_env()
    budget = yaml.safe_load(BUDGET_FILE.read_text())

    print('KF Harvest collector — fetching time entries…')
    snap = build_snapshot(budget, env)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(snap, indent=2))
    print(f'  Written: {OUTPUT_FILE}')
    print()
    print_status(snap)

    return 0


if __name__ == '__main__':
    sys.exit(main())
