"""Forecast income for the cash flow forecast, in tiers of confidence.

    receivable - invoices already sent: open items in GnuCash Accounts Receivable
    unbilled   - billable hours logged in Harvest, not yet invoiced
    fixed      - recurring, same amount each period       (income.yaml)
    predicted  - recurring, amount varies period to period (income.yaml)
    milestone  - agreed project payments not yet invoiced  (income.yaml)

The one source of forecast income: gnucash_parser merges it into `upcoming`, which
becomes accounts.json `upcoming_all`, so every consumer sees the same figures. Before
this, recurring income lived only in account_forecast_report.py and /account-forecast
showed outgoings-only balances (2026-10-08).
"""

import calendar
import re
from collections import defaultdict
from datetime import date, timedelta

TIERS = ('receivable', 'unbilled', 'fixed', 'predicted', 'milestone')
# Unbilled hours are base: the work is done and invoicing it is the studio's own action.
BASE_TIERS = ('receivable', 'unbilled', 'fixed')
# Shared with gnucash_parser's monthly bills. Matches the owner's draw window (~3 months)
# so later months never show income with no outgoings against them.
HORIZON_DAYS = 92
# A recurring occurrence counts as already invoiced if an AR invoice for the same
# client is dated within this many days of when that occurrence would be invoiced.
INVOICED_WINDOW_DAYS = 10


def is_base(entry):
    """Income a forecast may rely on: invoices sent, fixed recurring, and untiered
    hand-dated expected_income.yaml lines. Predicted income and milestones are upside."""
    return entry.get('type') == 'income' and entry.get('tier') in (None,) + BASE_TIERS


def load_config(config_dir):
    import yaml
    path = config_dir / 'income.yaml'
    if not path.exists():
        # No silent fallback: a forecast without its income is the failure this module exists to stop.
        raise RuntimeError(f"{path} not found -- forecast income config is required (see docs/utilities/income-forecast.md)")
    return yaml.safe_load(path.read_text()) or {}


def open_receivables(rows):
    """Open AR items, oldest first. Payments clear invoices FIFO within each AR leaf,
    so a part-paid invoice keeps its remainder open. Uses split quantity (the leaf's own
    currency), not value, which is in the transaction's currency.

    A payment with nothing open to clear (it sorted ahead of a same-day invoice, or was
    received before invoicing) is held as credit and applied to the next invoice, so the
    open items always sum to the leaf's balance."""
    by_leaf = defaultdict(list)
    for r in sorted((r for r in rows if 'Accounts Receivable' in r['path']), key=lambda r: r['date']):
        by_leaf[r['path']].append(r)

    open_items = []
    for leaf_rows in by_leaf.values():
        invoices = []
        credit = 0.0
        for r in leaf_rows:
            if r['qty'] > 0:
                invoices.append({'date': r['date'], 'desc': r['desc'], 'cur': r['cur'], 'open': r['qty']})
            else:
                credit += -r['qty']
            for inv in invoices:
                if credit <= 0.005:
                    break
                applied = min(inv['open'], credit)
                inv['open'] -= applied
                credit -= applied
        open_items += [i for i in invoices if i['open'] > 0.005]
    return sorted(open_items, key=lambda i: i['date'])


def ar_invoices(rows):
    """Every invoice ever booked to AR (open or paid), in the leaf's own currency."""
    return [{'date': date.fromisoformat(r['date']), 'desc': r['desc'], 'amount': r['qty']}
            for r in rows if 'Accounts Receivable' in r['path'] and r['qty'] > 0]


def _matches(pattern, desc):
    return bool(pattern) and re.search(pattern, desc, re.IGNORECASE) is not None


def _client_lag(cfg, pattern):
    settings = cfg.get('receivables') or {}
    client = next((c for c in settings.get('clients') or [] if c['match'] == pattern), None)
    return (client or {}).get('lag_days', settings.get('default_lag_days', 7))


def _already_invoiced(item, occurrence, invoices, cfg, same_amount):
    """True if AR already holds the invoice for this occurrence, so it is (or was) a
    receivable and must not be counted again as recurring or milestone income."""
    pattern = item.get('match')
    if not pattern:
        return False
    invoiced_on = occurrence - timedelta(days=_client_lag(cfg, pattern)) if occurrence else None
    for inv in invoices:
        if not _matches(pattern, inv['desc']):
            continue
        if same_amount and abs(inv['amount'] - item['amount']) > 0.01:
            continue
        if occurrence is None or abs((inv['date'] - invoiced_on).days) <= INVOICED_WINDOW_DAYS:
            return True
    return False


def _rate(currency, fx):
    if currency == 'EUR':
        return 1.0
    return fx.get(currency)


def _entry(label, tier, d, amount, currency, account, today, fx):
    rate = _rate(currency, fx)
    if rate is None:
        return None
    return {
        'label':           label,
        'date':            str(d),
        'days':            (d - today).days,
        'amount':          round(amount * rate, 2),
        'currency':        'EUR',
        'source_amount':   round(amount, 2),
        'source_currency': currency,
        'type':            'income',
        'tier':            tier,
        'account':         account,
    }


def _receivable_entries(rows, cfg, today, fx):
    settings = cfg.get('receivables') or {}
    default_lag = settings.get('default_lag_days', 7)
    clients = settings.get('clients') or []
    entries = []
    for inv in open_receivables(rows):
        client = next((c for c in clients if _matches(c['match'], inv['desc'])), None)
        lag = client.get('lag_days', default_lag) if client else default_lag
        expected = date.fromisoformat(inv['date']) + timedelta(days=lag)
        # Overdue: assume it lands tomorrow rather than in the past.
        expected = max(expected, today + timedelta(days=1))
        e = _entry(f"AR: {inv['desc']}", 'receivable', expected, inv['open'], inv['cur'],
                   client['account'] if client else 'Unknown', today, fx)
        if e:
            e['invoice_date'] = inv['date']
            entries.append(e)
    return entries


def harvest_projects(harvest):
    """Projects from a HarvestClient.fetch_all() result, or None if Harvest or its
    uninvoiced report failed -- so a failure is reported as missing, not as zero."""
    if not harvest or harvest.get('error') or (harvest.get('uninvoiced') or {}).get('error'):
        return None
    return harvest.get('projects')


def _client_rule(cfg, text):
    clients = (cfg.get('receivables') or {}).get('clients') or []
    return next((c for c in clients if _matches(c['match'], text)), None)


def _next_invoice_date(today):
    """Unbilled hours are invoiced at month end, the studio's usual cycle."""
    return date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])


def _unbilled_entries(harvest_projects, cfg, today, fx):
    """Billable hourly work logged in Harvest and not yet invoiced. Fixed-fee projects are
    left out (their payments are milestones), as is anything matching `unbilled.exclude`:
    hours already paid for by a recurring tier, such as a retainer or an Upwork contract."""
    settings = cfg.get('unbilled') or {}
    exclude = settings.get('exclude') or []
    default_lag = (cfg.get('receivables') or {}).get('default_lag_days', 7)
    invoiced_on = _next_invoice_date(today)
    entries = []
    for p in harvest_projects:
        amount = p.get('uninvoiced_amt') or 0
        if amount <= 0 or not p.get('is_billable') or p.get('is_fixed_fee'):
            continue
        name = f"{p.get('client', '')} | {p.get('name', '')}"
        if any(_matches(x, name) for x in exclude):
            continue
        rule = _client_rule(cfg, name)
        lag = rule.get('lag_days', default_lag) if rule else default_lag
        net = amount * (1 - (rule or {}).get('fee_pct', 0) / 100)
        e = _entry(f"Unbilled: {name}", 'unbilled', invoiced_on + timedelta(days=lag), net,
                   p.get('client_currency') or 'EUR', rule['account'] if rule else 'Unknown', today, fx)
        if e:
            e['hours'] = p.get('uninvoiced_hrs')
            entries.append(e)
    return entries


def _occurrences(pattern, today, end):
    start = max(date.fromisoformat(str(pattern.get('start', today))), today)
    stop = min(date.fromisoformat(str(pattern['end'])), end) if pattern.get('end') else end
    if pattern['cadence'] == 'weekly':
        d = start + timedelta(days=(pattern['weekday'] - start.weekday()) % 7)
        while d <= stop:
            yield d
            d += timedelta(days=7)
    elif pattern['cadence'] == 'monthly':
        y, m = start.year, start.month
        while True:
            d = date(y, m, min(pattern['day'], calendar.monthrange(y, m)[1]))
            if d > stop:
                return
            if d >= start:
                yield d
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    else:
        raise ValueError(f"income.yaml: unknown cadence {pattern['cadence']!r} for {pattern['label']}")


def forecast_income(rows, today, fx, cfg, harvest_projects=None):
    """All forecast income entries from today to HORIZON_DAYS, sorted by date.
    `fx` maps currency -> EUR rate, e.g. {'USD': 0.89, 'GBP': 1.18}.
    `harvest_projects` is HarvestClient.fetch_all()['projects']; None means Harvest was
    unavailable, and the caller must say so rather than forecast without unbilled work."""
    end = today + timedelta(days=HORIZON_DAYS)
    entries = _receivable_entries(rows, cfg, today, fx)
    entries += _unbilled_entries(harvest_projects or [], cfg, today, fx)
    invoices = ar_invoices(rows)

    for p in cfg.get('recurring') or []:
        if p.get('tier') not in ('fixed', 'predicted'):
            raise ValueError(f"income.yaml: recurring tier must be fixed or predicted ({p['label']})")
        for d in _occurrences(p, today, end):
            if _already_invoiced(p, d, invoices, cfg, same_amount=p['tier'] == 'fixed'):
                continue
            e = _entry(p['label'], p['tier'], d, p['amount'], p['currency'], p['account'], today, fx)
            if e:
                entries.append(e)

    for m in cfg.get('milestones') or []:
        d = date.fromisoformat(str(m['date']))
        # A milestone is invoiced once, so any AR invoice of its amount means it is
        # (or was) a receivable, whatever its date.
        if _already_invoiced(m, None, invoices, cfg, same_amount=True):
            continue
        if today <= d <= end:
            e = _entry(m['label'], 'milestone', d, m['amount'], m['currency'], m['account'], today, fx)
            if e:
                entries.append(e)

    return sorted(entries, key=lambda e: e['date'])
