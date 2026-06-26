"""
GnuCash collector — writes a Plutus-readable financial snapshot to
context/finance/accounts.json.

Tries the live dashboard API first (localhost:5555/api/data).
Falls back to parsing the GnuCash file directly if the server is not running.

Run: python3 studio/collectors/gnucash_collector.py
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

import os
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))
import gnucash_parser

CONTENT_DIR  = Path(os.getenv("STUDIO_CONTENT_DIR", Path(__file__).parents[2] / "context"))
GNUCASH_DIR  = Path(os.getenv("GNUCASH_DIR", '/media/data/Dropbox/Work/Admin/Financial/Accounting/GNUCash'))
GNUCASH_FILE = Path(os.getenv("GNUCASH_FILE", GNUCASH_DIR / 'accounts.gnucash'))
DASHBOARD_URL = 'http://localhost:5555/api/data'
OUTPUT_FILE  = CONTENT_DIR / 'finance' / 'accounts.json'

FX_FALLBACK = {'USD': 0.92, 'GBP': 1.17}


def fetch_from_server():
    """Return parsed data from the running dashboard server, or None if unreachable."""
    try:
        r = requests.get(DASHBOARD_URL, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def fetch_direct() -> dict:
    """Parse the GnuCash file directly, without the server."""
    fx = _get_fx_rates()
    gnucash = gnucash_parser.parse(str(GNUCASH_FILE), usd_rate=fx['USD'], gbp_rate=fx['GBP'])

    return {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'gnucash': gnucash,
        'fx': {
            'USD_TO_EUR': fx['USD'],
            'GBP_TO_EUR': fx['GBP'],
            'source': fx.get('source', 'fallback'),
        },
        'errors': [],
    }


def _get_fx_rates() -> dict:
    try:
        r = requests.get(
            'https://api.frankfurter.app/latest',
            params={'from': 'EUR', 'to': 'USD,GBP'},
            timeout=5,
        )
        r.raise_for_status()
        data = r.json()
        return {
            'USD': round(1 / data['rates']['USD'], 6),
            'GBP': round(1 / data['rates']['GBP'], 6),
            'source': f"frankfurter.app ({data['date']})",
        }
    except Exception:
        return {**FX_FALLBACK, 'source': 'fallback'}


def build_plutus_snapshot(data: dict) -> dict:
    """Flatten the raw API data into a Plutus-friendly snapshot."""
    g = data.get('gnucash', {})
    now = datetime.now(timezone.utc)

    # Last 3 months of P&L
    monthly_pl = g.get('monthly_pl', [])[-3:]

    # Current month (may be incomplete)
    current_month = now.strftime('%Y-%m')
    current_pl = next((m for m in g.get('monthly_pl', []) if m['month'] == current_month), None)

    # Upcoming bills in the next 30 days
    upcoming_30 = [u for u in g.get('upcoming', []) if u.get('days', 999) <= 30]

    # Liquid cash = Current Assets only (excludes Future Assets: IRPF, IVA, debts owed)
    balances = g.get('balances', [])
    liquid_eur = round(sum(
        b['eur'] for b in balances
        if b.get('name', '').startswith('Current Assets')
    ), 2)

    # Cashflow risk: upcoming 30d obligations vs liquid cash only
    upcoming_total = sum(u['amount'] for u in upcoming_30)
    balance_after  = liquid_eur - upcoming_total

    return {
        'generated_at': data['generated_at'],
        'fx': data.get('fx', {}),

        # Cash position
        'bank_balances': balances,
        'total_eur': g.get('total_eur', 0),   # all accounts incl. future assets
        'liquid_eur': liquid_eur,              # spendable cash (Current Assets only)

        # P&L
        'monthly_pl_recent': monthly_pl,
        'current_month': current_pl,
        'breakeven_allin': g.get('breakeven_allin', 4115.0),
        'fixed_costs': g.get('fixed_costs', 717.38),
        'owner_draw': g.get('owner_draw', 2566.67),

        # Upcoming obligations
        'upcoming_all': g.get('upcoming', []),
        'upcoming_30d': upcoming_30,
        'upcoming_30d_total': round(upcoming_total, 2),
        'balance_after_30d': round(balance_after, 2),

        # Recent income (for pipeline context)
        'recent_income': g.get('recent_income', [])[:10],

        # Harvest (time tracking) if available
        'harvest': data.get('harvest', {}),
    }


def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    print('GnuCash collector — fetching financial data…')

    # Try the live dashboard server first
    data = fetch_from_server()
    if data:
        print('  Source: dashboard server (localhost:5555)')
    else:
        print('  Server not running — parsing GnuCash file directly')
        data = fetch_direct()

    snapshot = build_plutus_snapshot(data)

    OUTPUT_FILE.write_text(json.dumps(snapshot, indent=2))
    print(f'  Written: {OUTPUT_FILE}')
    print(f'  Liquid cash: €{snapshot["liquid_eur"]:,.2f} (Current Assets only)')
    print(f'  Total incl. future assets: €{snapshot["total_eur"]:,.2f}')
    print(f'  Upcoming 30d: €{snapshot["upcoming_30d_total"]:,.2f}')
    print(f'  Liquid after 30d: €{snapshot["balance_after_30d"]:,.2f}')

    # Month-end crunch summary (end of current month only)
    from datetime import date as _date
    import calendar as _cal
    today = _date.today()
    month_end = str(_date(today.year, today.month, _cal.monthrange(today.year, today.month)[1]))
    eom_total = sum(u['amount'] for u in snapshot['upcoming_30d'] if u['date'] <= month_end)
    eom_balance = snapshot['liquid_eur'] - eom_total
    print(f'  End-of-month obligations ({month_end}): €{eom_total:,.2f}')
    print(f'  Liquid after month-end: €{eom_balance:,.2f}')

    errors = data.get('errors', [])
    if errors:
        print(f'  Warnings: {[e["message"] for e in errors]}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
