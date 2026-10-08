#!/usr/bin/env python3
import os
import sys
import threading
import webbrowser
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

from flask import Flask, jsonify, send_file, request
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / '.env')  # studio/.env — single source, no local override file

sys.path.insert(0, str(HERE))
import gnucash_parser
import income_forecast
import ops_status
from harvest_client import HarvestClient

app = Flask(__name__)

GNUCASH_PATH = os.environ['GNUCASH_FILE']  # no hardcoded fallback — must be set in studio/.env
HARVEST_TOKEN      = os.getenv('HARVEST_TOKEN', '')
HARVEST_ACCOUNT_ID = os.getenv('HARVEST_ACCOUNT_ID', '')
PIPELINE_API_URL   = os.getenv('PIPELINE_API_URL', 'http://localhost:5050')

# FX rate cache — refreshed at most once per hour
_fx_cache = {'rates': None, 'fetched_at': None, 'source': None}
_FX_TTL = timedelta(hours=1)
_FX_FALLBACK = {'USD': 0.92, 'GBP': 1.17}  # EUR per 1 foreign unit


def get_fx_rates():
    now = datetime.now(timezone.utc)
    if _fx_cache['rates'] and _fx_cache['fetched_at'] and (now - _fx_cache['fetched_at']) < _FX_TTL:
        return _fx_cache['rates'], _fx_cache['source']
    try:
        r = requests.get(
            'https://api.frankfurter.app/latest',
            params={'from': 'EUR', 'to': 'USD,GBP'},
            timeout=5,
        )
        r.raise_for_status()
        data = r.json()
        # data['rates'] = {'USD': 1.08, 'GBP': 0.84} — EUR per 1 EUR in foreign
        eur_per_usd = 1 / data['rates']['USD']
        eur_per_gbp = 1 / data['rates']['GBP']
        rates = {'USD': round(eur_per_usd, 6), 'GBP': round(eur_per_gbp, 6)}
        _fx_cache.update({'rates': rates, 'fetched_at': now, 'source': f"frankfurter.app ({data['date']})"})
        return rates, _fx_cache['source']
    except Exception as e:
        # Use last cached value if available, otherwise fallback constants
        if _fx_cache['rates']:
            return _fx_cache['rates'], f"cached (live fetch failed: {e})"
        return _FX_FALLBACK, f"fallback hardcoded (live fetch failed: {e})"


_STUDIO_CONTENT_DIR = Path(os.getenv('STUDIO_CONTENT_DIR', Path(__file__).resolve().parents[2] / 'context'))
KF_SNAPSHOT = _STUDIO_CONTENT_DIR / 'projects' / 'kf' / 'time_snapshot.json'


@app.route('/')
def index():
    return send_file(HERE / 'dashboard.html')


@app.route('/api/fx')
def api_fx():
    rates, source = get_fx_rates()
    return jsonify({'USD_TO_EUR': rates['USD'], 'GBP_TO_EUR': rates['GBP'], 'source': source})


@app.route('/api/kf')
def api_kf():
    if not KF_SNAPSHOT.exists():
        return jsonify({'error': 'Snapshot not found — run harvest_kf_collector.py'}), 404
    import json
    data = json.loads(KF_SNAPSHOT.read_text())
    return jsonify(data)


@app.route('/api/ops')
def api_ops():
    try:
        return jsonify(ops_status.summary())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/claude')
def api_claude():
    f = Path.home() / '.claude' / 'ratelimit-current.json'
    if not f.exists():
        return jsonify({'error': 'No rate-limit data at ~/.claude/ratelimit-current.json'}), 404
    import json
    d = json.loads(f.read_text())
    return jsonify({
        'pct': d.get('current_pct'),
        'reset_ts': d.get('reset_ts'),
        'weekly_pct': d.get('weekly_pct'),
        'weekly_reset_ts': d.get('weekly_reset_ts'),
        'read_at': datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).isoformat(),
    })


@app.route('/ops/log/<path:name>')
def ops_log(name):
    # Only logs that a crontab entry writes to are served, looked up by job name.
    job = next((j for j in ops_status.jobs() if j['name'] == name and j['log']), None)
    if not job or not Path(job['log']).is_file():
        return 'No log for that job', 404
    lines = Path(job['log']).read_text(errors='replace').splitlines()
    tail = int(request.args.get('lines', 500))
    body = '\n'.join(lines[-tail:]) if tail > 0 else '\n'.join(lines)
    header = f"# {job['log']} (last {min(tail, len(lines))} of {len(lines)} lines; ?lines=0 for all)\n\n"
    return header + body + '\n', 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/api/pipeline')
def api_pipeline():
    days = request.args.get('days', '7')
    try:
        r = requests.get(f'{PIPELINE_API_URL}/api/status', params={'days': days}, timeout=5)
        r.raise_for_status()
        return jsonify(r.json())
    except requests.exceptions.ConnectionError:
        return jsonify({'error': f'Pipeline API not reachable at {PIPELINE_API_URL}'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 502


@app.route('/api/pipeline/briefs')
def api_pipeline_briefs():
    try:
        r = requests.get(f'{PIPELINE_API_URL}/api/briefs', timeout=5)
        r.raise_for_status()
        return jsonify(r.json())
    except requests.exceptions.ConnectionError:
        return jsonify({'error': f'Pipeline API not reachable at {PIPELINE_API_URL}'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 502


@app.route('/api/pipeline/connects/<thread_id>', methods=['POST'])
def api_pipeline_connects(thread_id):
    try:
        r = requests.post(
            f'{PIPELINE_API_URL}/connects/{thread_id}',
            json=request.get_json(),
            timeout=5,
        )
        r.raise_for_status()
        return jsonify(r.json())
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Pipeline API not reachable'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 502


@app.route('/api/transactions')
def api_transactions():
    fx_rates, _ = get_fx_rates()
    try:
        data = gnucash_parser.parse(
            GNUCASH_PATH,
            usd_rate=fx_rates['USD'],
            gbp_rate=fx_rates['GBP'],
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    rows = data.get('transactions', [])

    q = request.args.get('q', '').lower()
    type_filter = request.args.get('type', '').upper()
    since = request.args.get('since', '')
    until = request.args.get('until', '')

    if q:
        rows = [r for r in rows if q in r['desc'].lower() or q in r['path'].lower()]
    if type_filter:
        rows = [r for r in rows if r['type'] == type_filter]
    if since:
        rows = [r for r in rows if r['date'] >= since]
    if until:
        rows = [r for r in rows if r['date'] <= until]

    rows = sorted(rows, key=lambda x: x['date'], reverse=True)
    limit = int(request.args.get('limit', 200))
    return jsonify({'count': len(rows), 'transactions': rows[:limit]})


@app.route('/api/data')
def api_data():
    return jsonify(_collect())


def _collect():
    """GnuCash + Harvest + FX, as served by /api/data and used by /api/cashflow."""
    # Reload .env on each request so credential changes take effect without restart
    load_dotenv(Path(__file__).resolve().parent.parent / '.env', override=True)
    harvest_token      = os.getenv('HARVEST_TOKEN', '').strip()
    harvest_account_id = os.getenv('HARVEST_ACCOUNT_ID', '').strip()

    errors = []
    result = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'gnucash':  {},
        'harvest':  {},
        'upwork':   {'configured': False},
        'fx':       {},
        'errors':   errors,
    }

    # Live FX rates
    fx_rates, fx_source = get_fx_rates()
    result['fx'] = {
        'USD_TO_EUR': fx_rates['USD'],
        'GBP_TO_EUR': fx_rates['GBP'],
        'source': fx_source,
    }

    # Harvest
    if harvest_token and harvest_account_id:
        try:
            client = HarvestClient(harvest_token, harvest_account_id)
            result['harvest'] = client.fetch_all(usd_rate=fx_rates['USD'], gbp_rate=fx_rates['GBP'])
        except Exception as e:
            errors.append({'source': 'harvest', 'message': str(e)})
            result['harvest'] = {'configured': True, 'error': str(e)}
    else:
        result['harvest'] = {'configured': False}
        if not harvest_token:
            errors.append({'source': 'harvest', 'message': 'HARVEST_TOKEN not set in .env'})

    # GNUCash — always attempt. After Harvest, so unbilled hours reach the income forecast.
    try:
        result['gnucash'] = gnucash_parser.parse(
            GNUCASH_PATH,
            usd_rate=fx_rates['USD'],
            gbp_rate=fx_rates['GBP'],
            harvest_projects=income_forecast.harvest_projects(result['harvest']),
        )
    except Exception as e:
        errors.append({'source': 'gnucash', 'message': str(e)})

    return result


@app.route('/api/cashflow')
def api_cashflow():
    """Per-account running balances over the forecast window, for the base case
    (invoices sent, unbilled hours, fixed income) and with every income tier."""
    from datetime import date as _date
    import cashflow

    d = _collect()
    g = d.get('gnucash') or {}
    if not g:
        return jsonify({'errors': d['errors']}), 500
    data = {'bank_balances': g.get('balances', []), 'upcoming_all': g.get('upcoming', [])}
    window_end = _date.today() + timedelta(days=income_forecast.HORIZON_DAYS)

    def scenario(tiers):
        shortfalls, tables, unassigned = cashflow.build_forecast(data, window_end, tiers)
        return {
            'shortfalls': [{'account': a, 'date': dt, 'label': lb, 'balance': round(bal, 2)}
                           for a, dt, lb, bal in shortfalls],
            'accounts': [{
                'name': name, 'start': round(start, 2),
                'rows': [{'date': dt, 'label': lb, 'type': ty, 'amount': round(delta, 2),
                          'balance': round(run, 2), 'shortfall': flag}
                         for dt, lb, ty, delta, run, flag in rows],
            } for name, start, rows in sorted(tables)],
            'unassigned': [{'date': t['date'], 'label': t['label'], 'amount': t['amount'],
                            'type': t.get('tier') or t.get('type')}
                           for t in unassigned if t['date'] <= str(window_end)],
        }

    income = [u for u in g.get('upcoming', []) if u.get('type') == 'income' and u['date'] <= str(window_end)]
    by_tier = {}
    for u in income:
        tier = u.get('tier') or 'expected'
        by_tier[tier] = round(by_tier.get(tier, 0) + u['amount'], 2)

    return jsonify({
        'generated_at': d['generated_at'],
        'window_end': str(window_end),
        'base_tiers': list(cashflow.BASE_TIERS),
        'income_by_tier': by_tier,
        'income_sources_missing': g.get('income_sources_missing', []),
        'base': scenario(cashflow.BASE_TIERS),
        'all': scenario(None),
        'errors': d['errors'],
    })


# Shown first, in this order; any other *.yaml in the config dir follows alphabetically.
CONFIG_ORDER = ['income.yaml', 'recurring-transactions.yaml', 'overheads.yaml',
                'rates.yaml', 'expected_income.yaml', 'bookkeeper-rules.yaml']


def _iso_dates(v):
    """YAML dates as ISO strings; Flask would otherwise send them as HTTP dates."""
    from datetime import date as _date
    if isinstance(v, dict):
        return {k: _iso_dates(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_iso_dates(x) for x in v]
    if isinstance(v, _date):
        return v.isoformat()
    return v


@app.route('/api/configs')
def api_configs():
    """Finance config files (FINANCE_CONFIG_DIR/*.yaml), parsed, for the Configs screen.
    Read-only: the YAML files stay the place to edit."""
    import yaml
    cfg_dir = gnucash_parser._finance_config_dir()
    files = sorted(cfg_dir.glob('*.yaml'),
                   key=lambda f: (CONFIG_ORDER.index(f.name) if f.name in CONFIG_ORDER else len(CONFIG_ORDER), f.name))
    out = []
    for f in files:
        try:
            docs = [x for x in yaml.safe_load_all(f.read_text(encoding='utf-8')) if x is not None]
            data = {}
            for doc in docs:
                data.update(doc if isinstance(doc, dict) else {'value': doc})
            out.append({'file': f.name, 'path': str(f),
                        'modified': datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).isoformat(),
                        'data': _iso_dates(data)})
        except Exception as e:
            out.append({'file': f.name, 'path': str(f), 'error': str(e)})
    # Not jsonify: it sorts keys, and table columns should keep the YAML file's order.
    import json as _json
    return app.response_class(_json.dumps({'dir': str(cfg_dir), 'files': out}, ensure_ascii=False),
                              mimetype='application/json')


def _open_browser():
    import time
    time.sleep(1)
    webbrowser.open('http://localhost:5555')


if __name__ == '__main__':
    print('Bain Design Financial Dashboard')
    print('================================')
    print(f'GNUCash: {GNUCASH_PATH}')
    print(f'Harvest: {"configured" if HARVEST_TOKEN else "not configured — add HARVEST_TOKEN to .env"}')
    print()
    print('Starting server at http://localhost:5555')
    threading.Thread(target=_open_browser, daemon=True).start()
    app.run(host='localhost', port=5555, debug=False)
