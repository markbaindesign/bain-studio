import gzip
import xml.etree.ElementTree as ET
from fractions import Fraction
from collections import defaultdict
from datetime import date
from pathlib import Path
import os

try:
    import yaml
    def _load_overheads():
        content_dir = Path(os.getenv("STUDIO_CONTENT_DIR", Path(__file__).parents[2] / "context"))
        oh_path = content_dir / "finance" / "overheads.yaml"
        if oh_path.exists():
            docs = list(yaml.safe_load_all(oh_path.read_text()))
            data = next((d for d in docs if isinstance(d, dict) and "reference_totals" in d), {})
            ref = data.get("reference_totals", {})
            return (
                ref.get("owner_draw_monthly", 2566.67),
                ref.get("breakeven_allin", 4115.0),
                ref.get("fixed_costs_approx", 717.38),
            )
        return 2566.67, 4115.0, 717.38
except ImportError:
    def _load_overheads():
        return 2566.67, 4115.0, 717.38


NS = {
    'gnc':   'http://www.gnucash.org/XML/gnc',
    'act':   'http://www.gnucash.org/XML/act',
    'trn':   'http://www.gnucash.org/XML/trn',
    'ts':    'http://www.gnucash.org/XML/ts',
    'split': 'http://www.gnucash.org/XML/split',
    'cmdty': 'http://www.gnucash.org/XML/cmdty',
}

UPCOMING_PATTERNS = [
    # (keyword_in_desc, label, day_of_month, type)
    ('Autonomos',  'Autónomos (Social Security)', 29, 'fixed'),
    ('Movistar',   'Movistar (Phone/Internet)',    1,  'fixed'),
    ('Crashplan',  'Crashplan Backup',             10, 'fixed'),
    ('Gsuite',     'Google Workspace',             3,  'fixed'),
    ('Cloudways',  'Cloudways Hosting',            7,  'fixed'),
    ('Asana',      'Asana',                        12, 'fixed'),
    ('Claude',     'Claude (Anthropic)',            23, 'fixed'),
    ('Github',     'GitHub Copilot',               15, 'fixed'),
    ('Algolia',    'Algolia',                      19, 'fixed'),
]


def _to_eur(val, currency, usd_rate, gbp_rate):
    if currency == 'EUR':
        return val
    if currency == 'USD':
        return val * usd_rate
    if currency == 'GBP':
        return val * gbp_rate
    return val


def _get_path(acc_id, accounts, depth=0):
    if depth > 10 or acc_id not in accounts:
        return ''
    a = accounts[acc_id]
    parent = _get_path(a['parent'], accounts, depth + 1) if a['parent'] else ''
    return (parent + ':' + a['name']).lstrip(':')


def parse(filepath, usd_rate=0.92, gbp_rate=1.17):
    owner_draw, breakeven_allin, fixed_costs = _load_overheads()

    opener = gzip.open if _is_gzip(filepath) else open
    with opener(filepath, 'rb') as f:
        raw = f.read()

    root = ET.fromstring(raw)
    book = root.find('gnc:book', NS)

    # --- Build account map ---
    accounts = {}
    for acc in book.findall('gnc:account', NS):
        aid   = acc.find('act:id', NS)
        aname = acc.find('act:name', NS)
        atype = acc.find('act:type', NS)
        apa   = acc.find('act:parent', NS)
        acmd  = acc.find('act:commodity', NS)
        cur   = None
        if acmd is not None:
            c = acmd.find('cmdty:id', NS)
            cur = c.text if c is not None else None
        if aid is not None:
            accounts[aid.text] = {
                'name':     aname.text if aname is not None else '?',
                'type':     atype.text if atype is not None else '?',
                'parent':   apa.text   if apa   is not None else None,
                'currency': cur,
                'path':     '',
            }

    for aid in accounts:
        accounts[aid]['path'] = _get_path(aid, accounts)

    # --- Parse transactions ---
    qty_balances = defaultdict(float)
    rows = []

    for trn in book.findall('gnc:transaction', NS):
        date_el = trn.find('trn:date-posted/ts:date', NS)
        desc_el = trn.find('trn:description', NS)
        txn_date = date_el.text[:10] if date_el is not None else '1970-01-01'
        desc     = desc_el.text if desc_el is not None else ''

        for sp in trn.findall('trn:splits/trn:split', NS):
            ae   = sp.find('split:account', NS)
            ve   = sp.find('split:value', NS)
            qe   = sp.find('split:quantity', NS)
            aid2 = ae.text if ae is not None else None
            val  = float(Fraction(ve.text)) if ve is not None else 0.0
            qty  = float(Fraction(qe.text)) if qe is not None else 0.0

            if aid2 and aid2 in accounts:
                a2  = accounts[aid2]
                cur = a2['currency'] or 'EUR'
                eur = _to_eur(val, cur, usd_rate, gbp_rate)
                qty_balances[aid2] += qty
                rows.append({
                    'date': txn_date,
                    'desc': desc,
                    'path': a2['path'],
                    'type': a2['type'],
                    'cur':  cur,
                    'val':  val,
                    'eur':  eur,
                })

    # --- Current balances (all asset accounts, matching GnuCash total) ---
    balances = []
    total_eur = 0.0
    for aid, a in sorted(accounts.items(), key=lambda x: x[1]['path']):
        if a['type'] not in ('BANK', 'CASH', 'ASSET'):
            continue
        if 'Root Account:Assets' not in a['path']:
            continue
        qty = qty_balances.get(aid, 0.0)
        if abs(qty) < 0.01:
            continue
        cur = a['currency'] or 'EUR'
        eur = _to_eur(qty, cur, usd_rate, gbp_rate)
        total_eur += eur
        name = a['path'].replace('Root Account:Assets:', '')
        balances.append({
            'name':     name,
            'balance':  round(qty, 2),
            'currency': cur,
            'eur':      round(eur, 2),
        })

    # --- Monthly P&L (2025 onwards) ---
    monthly_inc = defaultdict(float)
    monthly_exp = defaultdict(float)
    for r in rows:
        if r['date'] < '2025-01-01':
            continue
        m = r['date'][:7]
        if r['type'] == 'INCOME' and r['val'] < 0:
            monthly_inc[m] += abs(r['eur'])
        elif r['type'] == 'EXPENSE' and r['val'] > 0:
            monthly_exp[m] += r['eur']

    all_months = sorted(set(list(monthly_inc) + list(monthly_exp)))
    monthly_pl = []
    for m in all_months:
        inc = monthly_inc.get(m, 0.0)
        exp = monthly_exp.get(m, 0.0)
        monthly_pl.append({
            'month':     m,
            'income':    round(inc, 2),
            'expenses':  round(exp, 2),
            'draw':      owner_draw,
            'net':       round(inc - exp - owner_draw, 2),
        })

    # --- 2025 expense mix by top-level category ---
    cat_exp = defaultdict(float)
    for r in rows:
        if r['type'] != 'EXPENSE' or r['val'] <= 0:
            continue
        if r['date'] < '2025-01-01' or r['date'] >= '2026-01-01':
            continue
        parts = r['path'].replace('Root Account:Expenses:', '').split(':')
        cat_exp[parts[0]] += r['eur']

    # --- Upcoming expenses ---
    today = date.today()
    upcoming = _compute_upcoming(rows, today, owner_draw)

    # --- Last income entries for context ---
    income_rows = sorted(
        [r for r in rows if r['type'] == 'INCOME' and r['val'] < 0],
        key=lambda x: x['date'],
        reverse=True,
    )[:20]
    recent_income = [
        {'date': r['date'], 'desc': r['desc'], 'eur': round(abs(r['eur']), 2),
         'cur': r['cur'], 'amount': round(abs(r['val']), 2)}
        for r in income_rows
    ]

    return {
        'balances':        balances,
        'total_eur':       round(total_eur, 2),
        'monthly_pl':      monthly_pl,
        'cat_exp':         dict(cat_exp),
        'upcoming':        upcoming,
        'recent_income':   recent_income,
        'owner_draw':      owner_draw,
        'breakeven_allin': breakeven_allin,
        'fixed_costs':     fixed_costs,
    }


def _compute_upcoming(rows, today, owner_draw):
    upcoming = []

    # Owner's draw — end of each month
    for delta_months in range(3):
        m = today.month + delta_months
        y = today.year + (m - 1) // 12
        m = ((m - 1) % 12) + 1
        import calendar
        last_day = calendar.monthrange(y, m)[1]
        d = date(y, m, last_day)
        if d >= today:
            upcoming.append({
                'label':    "Owner's Draw",
                'date':     str(d),
                'amount':   round(owner_draw),
                'currency': 'EUR',
                'type':     'draw',
                'days':     (d - today).days,
            })

    # Pattern-based recurring bills — amounts derived from transaction history
    exp_rows = [r for r in rows if r['type'] == 'EXPENSE' and r['val'] > 0 and r['date'] >= '2025-01-01']

    for keyword, label, typical_day, bill_type in UPCOMING_PATTERNS:
        matches = [r for r in exp_rows if keyword.lower() in r['desc'].lower()]
        if not matches:
            continue
        last = max(matches, key=lambda x: x['date'])
        last_date = date.fromisoformat(last['date'])
        monthly_totals = defaultdict(float)
        for r in matches:
            monthly_totals[r['date'][:7]] += r['eur']
        avg_amt = sum(monthly_totals.values()) / len(monthly_totals)

        for delta in range(3):
            m = last_date.month + delta
            y = last_date.year + (m - 1) // 12
            m = ((m - 1) % 12) + 1
            import calendar
            max_day = calendar.monthrange(y, m)[1]
            d = date(y, m, min(typical_day, max_day))
            if d > today:
                upcoming.append({
                    'label':    label,
                    'date':     str(d),
                    'amount':   round(avg_amt, 2),
                    'currency': 'EUR',
                    'type':     bill_type,
                    'days':     (d - today).days,
                })
                break

    # Quarterly taxes — Mod 130, Mod 111, IVA, Gestor
    quarterly = [
        ('Mod. 130', 'Mod 130 (Income Tax)',  'tax'),
        ('Mod. 111', 'Mod 111 (Withholding)', 'tax'),
        ('IVA',      'IVA',                   'tax'),
        ('Gestor',   'Gestor (Accountant)',    'fixed'),
    ]
    for keyword, label, bill_type in quarterly:
        matches = [r for r in exp_rows if keyword.lower() in r['desc'].lower() or keyword.lower() in r['path'].lower()]
        if not matches:
            continue
        last = max(matches, key=lambda x: x['date'])
        last_date = date.fromisoformat(last['date'])
        avg_amt = sum(r['eur'] for r in matches) / len(matches)

        next_m = last_date.month + 3
        next_y = last_date.year + (next_m - 1) // 12
        next_m = ((next_m - 1) % 12) + 1
        import calendar
        max_day = calendar.monthrange(next_y, next_m)[1]
        d = date(next_y, next_m, min(last_date.day, max_day))
        if d >= today:
            upcoming.append({
                'label':    label,
                'date':     str(d),
                'amount':   round(avg_amt, 2),
                'currency': 'EUR',
                'type':     bill_type,
                'days':     (d - today).days,
            })

    upcoming.sort(key=lambda x: x['date'])
    return upcoming[:15]


def _is_gzip(filepath):
    with open(filepath, 'rb') as f:
        return f.read(2) == b'\x1f\x8b'
