import gzip
import xml.etree.ElementTree as ET
from fractions import Fraction
from collections import defaultdict
from datetime import date
from pathlib import Path
import os

def _finance_config_dir():
    value = os.getenv("FINANCE_CONFIG_DIR")
    if not value:
        raise RuntimeError("FINANCE_CONFIG_DIR must be set (see studio/.env) -- no hardcoded fallback")
    return Path(value)


def _finance_data_dir():
    """Generated data + docs (accounts.json, aletheia-codex.md) -- distinct from
    FINANCE_CONFIG_DIR, which holds only user-editable settings."""
    value = os.getenv("FINANCE_DATA_DIR")
    if not value:
        raise RuntimeError("FINANCE_DATA_DIR must be set (see studio/.env) -- no hardcoded fallback")
    return Path(value)


def _load_overheads():
    import yaml
    oh_path = _finance_config_dir() / "overheads.yaml"
    if not oh_path.exists():
        raise RuntimeError(f"overheads.yaml not found at {oh_path} -- no hardcoded fallback")
    docs = list(yaml.safe_load_all(oh_path.read_text()))
    data = next((d for d in docs if isinstance(d, dict) and "reference_totals" in d), {})
    ref = data["reference_totals"]
    return (
        ref["owner_draw_monthly"],
        ref["breakeven_allin"],
        ref["fixed_costs_approx"],
    )


NS = {
    'gnc':   'http://www.gnucash.org/XML/gnc',
    'act':   'http://www.gnucash.org/XML/act',
    'trn':   'http://www.gnucash.org/XML/trn',
    'ts':    'http://www.gnucash.org/XML/ts',
    'split': 'http://www.gnucash.org/XML/split',
    'cmdty': 'http://www.gnucash.org/XML/cmdty',
}

def _load_upcoming_patterns():
    """Recurring bill -> billing account map, edited as data, not code -- see
    FINANCE_CONFIG_DIR/recurring-transactions.yaml. No hardcoded fallback: billing-
    account moves (BBVA -> Wise etc.) must be reflected there, not silently guessed."""
    import yaml
    cfg_path = _finance_config_dir() / "recurring-transactions.yaml"
    if not cfg_path.exists():
        raise RuntimeError(f"recurring-transactions.yaml not found at {cfg_path} -- no hardcoded fallback")
    docs = list(yaml.safe_load_all(cfg_path.read_text()))
    data = next((d for d in docs if isinstance(d, dict) and "recurring" in d), {})
    entries = data["recurring"]
    return [
        (e["keyword"], e["label"], e["day_of_month"], e["type"], e["billing_account"])
        for e in entries
    ]


UPCOMING_PATTERNS = _load_upcoming_patterns()


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
                    'desc': desc or '',
                    'path': a2['path'] or '',
                    'type': a2['type'] or '',
                    'cur':  cur,
                    'val':  val,
                    'eur':  eur,
                })

    # --- Current balances (all asset accounts, matching GnuCash total) ---
    balances = []
    total_eur = 0.0
    liquid_eur = 0.0
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
        is_liquid = 'Suspense' not in a['path'] and 'Future' not in a['path']
        if is_liquid:
            liquid_eur += eur
        name = a['path'].replace('Root Account:Assets:', '')
        balances.append({
            'name':     name,
            'balance':  round(qty, 2),
            'currency': cur,
            'eur':      round(eur, 2),
            'liquid':   is_liquid,
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

    # --- Upcoming expenses + manually-forecast incoming payments ---
    today = date.today()
    upcoming = _compute_upcoming(rows, today, owner_draw)
    expected_income = _load_expected_income(today)
    upcoming = sorted(upcoming + expected_income, key=lambda x: x['date'])

    # --- Balance after 30 days of known bills (income entries offset, not add to, obligations) ---
    due_30d    = sum(u['amount'] for u in upcoming if u.get('days', 999) <= 30 and u.get('type') != 'income')
    income_30d = sum(u['amount'] for u in upcoming if u.get('days', 999) <= 30 and u.get('type') == 'income')
    balance_after_30d = round(liquid_eur - due_30d + income_30d, 2)

    # --- BBVA-specific forecast — the account Spanish DDs actually draw from ---
    bbva_balance = next((b['eur'] for b in balances if 'BBVA' in b['name']), 0.0)
    bbva_due_30d = sum(
        u['amount'] for u in upcoming
        if u.get('account') == 'BBVA EUR' and u.get('type') != 'income' and u.get('days', 999) <= 30
    )
    bbva_income_30d = sum(
        u['amount'] for u in upcoming
        if u.get('account') == 'BBVA EUR' and u.get('type') == 'income' and u.get('days', 999) <= 30
    )
    bbva_balance_after_30d = round(bbva_balance - bbva_due_30d + bbva_income_30d, 2)
    bbva_forecast = {
        'balance':           round(bbva_balance, 2),
        'due_30d':           round(bbva_due_30d, 2),
        'income_30d':        round(bbva_income_30d, 2),
        'balance_after_30d': bbva_balance_after_30d,
        'shortfall':         bbva_balance_after_30d < 0,
    }

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
        'balances':          balances,
        'total_eur':         round(total_eur, 2),
        'liquid_eur':        round(liquid_eur, 2),
        'balance_after_30d': balance_after_30d,
        'income_30d':        round(income_30d, 2),
        'bbva_forecast':     bbva_forecast,
        'monthly_pl':        monthly_pl,
        'cat_exp':           dict(cat_exp),
        'upcoming':          upcoming,
        'expected_income':   expected_income,
        'recent_income':     recent_income,
        'owner_draw':        owner_draw,
        'breakeven_allin': breakeven_allin,
        'fixed_costs':     fixed_costs,
        'transactions':    rows,
    }


def _quarter_start(d):
    return date(d.year, ((d.month - 1) // 3) * 3 + 1, 1)


def _compute_upcoming(rows, today, owner_draw):
    upcoming = []

    # Owner's draw — end of month, per aletheia-codex.md §"Owner's Draw" (source: BBVA EUR)
    import calendar
    for delta_months in range(3):
        m = today.month + delta_months
        y = today.year + (m - 1) // 12
        m = ((m - 1) % 12) + 1
        max_day = calendar.monthrange(y, m)[1]
        d = date(y, m, max_day)
        if d >= today:
            upcoming.append({
                'label':    "Owner's Draw",
                'date':     str(d),
                'amount':   round(owner_draw),
                'currency': 'EUR',
                'type':     'draw',
                'account':  'BBVA EUR',
                'days':     (d - today).days,
            })

    # Pattern-based recurring bills — amounts derived from transaction history
    exp_rows = [r for r in rows if r['type'] == 'EXPENSE' and r['val'] > 0 and r['date'] >= '2025-01-01']

    for keyword, label, typical_day, bill_type, billing_account in UPCOMING_PATTERNS:
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
                    'account':  billing_account,
                    'days':     (d - today).days,
                })
                break

    # Quarterly taxes — Mod 130, Mod 111, IVA, Gestor
    # Deadlines per aletheia-codex: Q1=20 Apr, Q2=20 Jul, Q3=20 Oct, Q4=30 Jan
    # Gestor follows the same quarterly pattern but uses the actual payment day.
    quarterly = [
        ('Mod. 130', 'Mod 130 (Income Tax)',  'tax'),
        ('Mod. 111', 'Mod 111 (Withholding)', 'tax'),
        ('IVA',      'IVA',                   'tax'),
        ('Gestor',   'Gestor (Accountant)',    'fixed'),
    ]
    # All quarterly filings and the gestor draw from BBVA per aletheia-codex.md §3
    QUARTERLY_ACCOUNT = 'BBVA EUR'

    # Quarter-end month → (filing month, filing day)
    TAX_DEADLINE = {3: (4, 20), 6: (7, 20), 9: (10, 20), 12: (1, 30)}
    confirmed_filings = _load_confirmed_tax_filings()

    # Prefer the gestor's confirmed figures (aletheia-codex.md §8) for any filing still
    # upcoming — historical averaging is only a fallback for quarters not yet confirmed.
    confirmed_labels_added = set()
    next_filing = min(
        (f for f in confirmed_filings if f['due_date'] >= today),
        key=lambda f: f['due_date'],
        default=None,
    )
    if next_filing:
        for match_key, label in (('iva', 'IVA'), ('mod130', 'Mod 130 (Income Tax)'), ('mod111', 'Mod 111 (Withholding)')):
            d = next_filing['due_date']
            upcoming.append({
                'label':    label,
                'date':     str(d),
                'amount':   round(next_filing[match_key], 2),
                'currency': 'EUR',
                'type':     'tax',
                'account':  QUARTERLY_ACCOUNT,
                'days':     (d - today).days,
                'source':   'confirmed (gestor)',
            })
            confirmed_labels_added.add(label)

    for keyword, label, bill_type in quarterly:
        if label in confirmed_labels_added:
            continue
        matches = [r for r in exp_rows if keyword.lower() in r['desc'].lower() or keyword.lower() in r['path'].lower()]
        if not matches:
            continue
        import calendar

        last = max(matches, key=lambda x: x['date'])
        last_date = date.fromisoformat(last['date'])
        avg_amt = sum(r['eur'] for r in matches) / len(matches)

        next_m = last_date.month + 3
        next_y = last_date.year + (next_m - 1) // 12
        next_m = ((next_m - 1) % 12) + 1

        if bill_type == 'tax' and next_m in TAX_DEADLINE:
            # Use official filing deadline (20th of month after quarter-end, or 30 Jan for Q4)
            file_m, file_d = TAX_DEADLINE[next_m]
            file_y = next_y + (1 if file_m < next_m else 0)
            d = date(file_y, file_m, file_d)
        else:
            max_day = calendar.monthrange(next_y, next_m)[1]
            d = date(next_y, next_m, min(last_date.day, max_day))

        if d >= today:
            entry_amt = avg_amt
            extra = {}
            if keyword == 'Mod. 130':
                # Deduct IRPF withheld by Spanish clients this quarter
                q_start = str(_quarter_start(today))
                irpf_withheld = sum(
                    r['eur'] for r in rows
                    if 'IRPF Retenido' in r.get('path', '')
                    and r['date'] >= q_start
                    and r['val'] > 0  # debit = asset increase (withheld from client)
                )
                if irpf_withheld > 0:
                    entry_amt = max(0.0, avg_amt - irpf_withheld)
                    extra['irpf_deducted'] = round(irpf_withheld, 2)
            upcoming.append({
                'label':    label,
                'date':     str(d),
                'amount':   round(entry_amt, 2),
                'currency': 'EUR',
                'type':     bill_type,
                'account':  QUARTERLY_ACCOUNT,
                'days':     (d - today).days,
                **extra,
            })

    upcoming.sort(key=lambda x: x['date'])
    return upcoming[:15]


_FILING_ROW_RE = __import__('re').compile(
    r"^\|\s*Q(\d)\s+(\d{4})\s*\|\s*€?([\d,\.]+)\s*\|\s*€?([\d,\.]+)\s*\|\s*€?([\d,\.]+)\s*\|",
    __import__('re').MULTILINE,
)

# Quarter number → (filing month, filing day); Q4 files in January of the following year
_QUARTER_DEADLINE = {1: (4, 20), 2: (7, 20), 3: (10, 20), 4: (1, 30)}


def _load_confirmed_tax_filings():
    """Parse the Quarterly Filing Log (aletheia-codex.md §8) for gestor-confirmed amounts."""
    path = _finance_data_dir() / "aletheia-codex.md"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")

    filings = []
    for m in _FILING_ROW_RE.finditer(text):
        q, year, iva, mod130, mod111 = m.groups()
        q, year = int(q), int(year)
        file_m, file_d = _QUARTER_DEADLINE.get(q, (None, None))
        if file_m is None:
            continue
        file_y = year + (1 if q == 4 else 0)
        try:
            due_date = date(file_y, file_m, file_d)
        except ValueError:
            continue
        filings.append({
            'quarter':  f'Q{q} {year}',
            'due_date': due_date,
            'iva':      float(iva.replace(',', '')),
            'mod130':   float(mod130.replace(',', '')),
            'mod111':   float(mod111.replace(',', '')),
        })
    return filings


def _load_expected_income(today):
    """Manually-maintained forecast of incoming payments — FINANCE_CONFIG_DIR/expected_income.yaml."""
    try:
        import yaml
    except ImportError:
        return []
    path = _finance_config_dir() / "expected_income.yaml"
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except Exception:
        return []

    entries = []
    for item in (data.get('income') or []):
        try:
            d = date.fromisoformat(str(item['date']))
        except Exception:
            continue
        if d < today:
            continue
        entries.append({
            'label':      item.get('label', 'Expected income'),
            'date':       str(d),
            'amount':     float(item.get('amount', 0)),
            'currency':   item.get('currency', 'EUR'),
            'account':    item.get('account', 'Unknown'),
            'type':       'income',
            'confidence': item.get('confidence', 'estimated'),
            'days':       (d - today).days,
        })
    return entries


def _is_gzip(filepath):
    with open(filepath, 'rb') as f:
        return f.read(2) == b'\x1f\x8b'
