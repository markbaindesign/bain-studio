#!/usr/bin/env python3
import os
import sys
import threading
import webbrowser
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

from flask import Flask, jsonify, send_file
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE / '.env')

sys.path.insert(0, str(HERE))
import gnucash_parser
from harvest_client import HarvestClient

app = Flask(__name__)

GNUCASH_PATH = os.getenv(
    'GNUCASH_PATH',
    '/media/data/Dropbox/Work/Admin/Financial/Accounting/GNUCash/accounts.gnucash',
)
HARVEST_TOKEN      = os.getenv('HARVEST_TOKEN', '')
HARVEST_ACCOUNT_ID = os.getenv('HARVEST_ACCOUNT_ID', '')

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


KF_SNAPSHOT = Path(__file__).resolve().parents[2] / 'context' / 'projects' / 'kf' / 'time_snapshot.json'


@app.route('/')
def index():
    return send_file(HERE / 'dashboard.html')


@app.route('/api/kf')
def api_kf():
    if not KF_SNAPSHOT.exists():
        return jsonify({'error': 'Snapshot not found — run harvest_kf_collector.py'}), 404
    import json
    data = json.loads(KF_SNAPSHOT.read_text())
    return jsonify(data)


@app.route('/api/data')
def api_data():
    # Reload .env on each request so credential changes take effect without restart
    load_dotenv(Path(__file__).parent / '.env', override=True)
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

    # GNUCash — always attempt
    try:
        result['gnucash'] = gnucash_parser.parse(
            GNUCASH_PATH,
            usd_rate=fx_rates['USD'],
            gbp_rate=fx_rates['GBP'],
        )
    except Exception as e:
        errors.append({'source': 'gnucash', 'message': str(e)})

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

    return jsonify(result)


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
