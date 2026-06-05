"""
Harvest KF collector — writes a time-budget snapshot for the Khyentse Foundation
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
ENV_FILE    = ROOT / 'studio' / 'dashboard' / '.env'

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

    year_target   = round(paced_monthly * months_remaining + completed_hours, 2)  # == adjusted_annual by definition
    year_variance = round(year_hours - round(paced_monthly * months_elapsed, 2), 2)

    # Year target to date: completed actual + current-month paced target
    year_target_to_date = round(completed_hours + paced_monthly, 2)
    year_variance       = round(year_hours - year_target_to_date, 2)

    month_hours    = by_month.get(current_month, 0.0)
    month_target   = round(paced_monthly, 2)
    month_variance = round(month_hours - month_target, 2)

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
        'by_month':                  by_month,
    }


def print_status(snap):
    yr       = snap['year']
    y_logged = snap['year_hours_logged']
    y_base   = snap['annual_hours_target']
    y_adj    = snap['adjusted_annual_target']
    y_var    = snap['year_variance']
    co       = snap['carry_over_hours']
    paced    = snap['paced_monthly_target']
    m_name   = datetime.strptime(snap['current_month'], '%Y-%m').strftime('%b')
    m_logged = snap['month_hours_logged']
    m_target = snap['month_hours_target']
    m_var    = snap['month_variance']

    y_dir = 'ahead of' if y_var >= 0 else 'behind'
    m_dir = 'ahead of' if m_var >= 0 else 'behind'

    if co != 0:
        co_dir = 'owed from' if co > 0 else 'credit from'
        print(f'Carry-over ({snap["carry_over_from_year"]}): {abs(co):.1f}h {co_dir} '
              f'{snap["carry_over_from_year"]} '
              f'(logged {snap["prev_year_logged"]:.1f}h of {snap["prev_year_target"]:.1f}h target)')
        print(f'Adjusted annual target: {y_base:.1f}h base {co:+.1f}h = {y_adj:.1f}h')
    print(f'Paced monthly target: {paced:.1f}h '
          f'({snap["months_remaining"]} months left, {snap["completed_hours"]:.1f}h logged in completed months)')
    print(f'Budget for year {yr}: {y_logged:.1f}/{y_adj:.1f}h — {abs(y_var):.1f}h {y_dir} target')
    print(f'Budget for month ({m_name}): {m_logged:.1f}/{m_target:.1f}h — {abs(m_var):.1f}h {m_dir} target')


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
