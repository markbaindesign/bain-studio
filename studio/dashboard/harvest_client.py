import requests
from datetime import date, timedelta

BASE = 'https://api.harvestapp.com/api/v2'


class HarvestClient:
    def __init__(self, token, account_id):
        self.headers = {
            'Authorization':      f'Bearer {token}',
            'Harvest-Account-Id': str(account_id),
            'User-Agent':         'BainDesign-Dashboard/1.0',
        }

    def _get(self, path, params=None):
        r = requests.get(f'{BASE}{path}', headers=self.headers, params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_active_projects(self):
        data = self._get('/projects', {'is_active': 'true', 'per_page': 100})
        projects = []
        for p in data.get('projects', []):
            client     = p.get('client') or {}
            budget     = p.get('budget') or 0
            spent      = p.get('budget_spent') or 0
            remaining  = budget - spent if budget else None
            projects.append({
                'id':               p['id'],
                'name':             p['name'],
                'client':           client.get('name', 'Unknown'),
                'client_currency':  client.get('currency', 'USD'),
                'is_billable':      p.get('is_billable', False),
                'is_fixed_fee':     p.get('is_fixed_fee', False),
                'bill_by':          p.get('bill_by', ''),
                'budget':           round(budget, 2) if budget else None,
                'budget_by':        p.get('budget_by', ''),
                'budget_spent':     round(spent, 2),
                'budget_remaining': round(remaining, 2) if remaining is not None else None,
                'budget_pct':       round(spent / budget * 100, 1) if budget else None,
                'hourly_rate':      p.get('hourly_rate'),
                'fee':              p.get('fee'),
                'starts_on':        p.get('starts_on', ''),
                'ends_on':          p.get('ends_on', ''),
                'notes':            p.get('notes', '') or '',
            })
        return projects

    def get_outstanding_invoices(self):
        data = self._get('/invoices', {'state': 'open', 'per_page': 100})
        invoices = []
        for inv in data.get('invoices', []):
            client_name = (inv.get('client') or {}).get('name', 'Unknown')
            invoices.append({
                'number':     inv.get('number', ''),
                'client':     client_name,
                'amount':     round(inv.get('amount', 0), 2),
                'due_amount': round(inv.get('due_amount', 0), 2),
                'due_date':   inv.get('due_date', ''),
                'issue_date': inv.get('issue_date', ''),
                'currency':   inv.get('currency', 'EUR'),
                'state':      inv.get('state', ''),
            })
        invoices.sort(key=lambda x: x['due_date'] or '')
        return invoices

    def get_uninvoiced_total(self, usd_rate=0.92, gbp_rate=1.17):
        today     = date.today()
        from_date = (today - timedelta(days=364)).isoformat()
        to_date   = today.isoformat()
        try:
            data    = self._get('/reports/uninvoiced', {'from': from_date, 'to': to_date})
            results = data.get('results', [])

            # Three buckets:
            # 1. clearly_uninvoiced: positive amount, zero invoiced — ready to bill
            # 2. partial: positive amount but invoices exist — fixed-fee/retainer, hours show as
            #    "uninvoiced" even though covered by invoice; misleading as money owed
            # 3. credits (negative): deposit received in advance or overpayment — ignored
            clearly_uninvoiced = []
            partial            = []
            total_eur          = 0.0
            # Also build a project_id → uninvoiced lookup for the projects tab
            by_project_id      = {}

            for r in results:
                amt      = r.get('uninvoiced_amount') or 0
                inv_amt  = r.get('invoiced_amount') or 0
                uninv_hr = r.get('uninvoiced_hours') or 0
                proj_id  = r.get('project_id')
                if amt <= 0:
                    continue
                cur = r.get('currency', 'EUR')
                eur = amt if cur == 'EUR' else (amt * usd_rate if cur == 'USD' else amt * gbp_rate if cur == 'GBP' else amt)
                row = {
                    'project_id':     proj_id,
                    'project':        r.get('project_name', ''),
                    'client':         r.get('client_name', ''),
                    'uninvoiced':     round(amt, 2),
                    'uninvoiced_eur': round(eur, 2),
                    'uninvoiced_hrs': round(uninv_hr, 2),
                    'invoiced_amt':   round(inv_amt, 2),
                    'currency':       cur,
                    'is_partial':     inv_amt > 0,
                }
                by_project_id[proj_id] = row
                if inv_amt == 0:
                    clearly_uninvoiced.append(row)
                    total_eur += eur
                else:
                    partial.append(row)

            clearly_uninvoiced.sort(key=lambda x: -x['uninvoiced_eur'])
            partial.sort(key=lambda x: -x['uninvoiced_eur'])
            return {
                'total_eur':     round(total_eur, 2),
                'by_project':    clearly_uninvoiced,
                'partial':       partial,
                'by_project_id': by_project_id,
            }
        except Exception:
            return {'total_eur': 0, 'by_project': [], 'partial': [], 'by_project_id': {}}

    def get_earnings(self, usd_rate=0.92, gbp_rate=1.17):
        today       = date.today()
        week_start  = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        periods = [
            ('today',      today.isoformat(),       today.isoformat()),
            ('this_week',  week_start.isoformat(),  today.isoformat()),
            ('this_month', month_start.isoformat(), today.isoformat()),
        ]
        result = {}
        for key, fd, td in periods:
            try:
                rows   = self._get('/reports/time/clients', {'from': fd, 'to': td}).get('results', [])
                hours  = sum(r.get('total_hours', 0) or 0 for r in rows)
                amount = sum(r.get('billable_amount', 0) or 0 for r in rows)
                result[key] = {'hours': round(hours, 1), 'amount': round(amount, 2), 'eur': round(amount * usd_rate, 2)}
            except Exception:
                result[key] = {'hours': 0, 'amount': 0, 'eur': 0}
        return result

    def get_project_time_this_month(self):
        today       = date.today()
        month_start = today.replace(day=1).isoformat()
        try:
            rows = self._get('/reports/time/projects', {'from': month_start, 'to': today.isoformat()}).get('results', [])
            return {
                r['project_id']: {
                    'total_hours':    round(r.get('total_hours', 0) or 0, 1),
                    'billable_hours': round(r.get('billable_hours', 0) or 0, 1),
                    'billable_amount': round(r.get('billable_amount', 0) or 0, 2),
                    'currency':       r.get('currency', 'USD'),
                }
                for r in rows
            }
        except Exception:
            return {}

    def fetch_all(self, usd_rate=0.92, gbp_rate=1.17):
        projects    = self.get_active_projects()
        invoices    = self.get_outstanding_invoices()
        uninvoiced  = self.get_uninvoiced_total(usd_rate=usd_rate, gbp_rate=gbp_rate)
        earnings    = self.get_earnings(usd_rate=usd_rate, gbp_rate=gbp_rate)
        month_time  = self.get_project_time_this_month()

        # Enrich each project with this-month time + uninvoiced data
        uninv_lookup = uninvoiced.get('by_project_id', {})
        for p in projects:
            pid = p['id']
            mt  = month_time.get(pid, {})
            ui  = uninv_lookup.get(pid, {})
            p['month_hours']          = mt.get('total_hours', 0)
            p['month_billable_hours'] = mt.get('billable_hours', 0)
            p['month_billable_amount']= mt.get('billable_amount', 0)
            p['uninvoiced_hrs']       = ui.get('uninvoiced_hrs', 0)
            p['uninvoiced_amt']       = ui.get('uninvoiced', 0)
            p['uninvoiced_eur']       = ui.get('uninvoiced_eur', 0)
            p['uninvoiced_is_partial']= ui.get('is_partial', False)

        return {
            'projects':      projects,
            'invoices':      invoices,
            'uninvoiced':    uninvoiced,
            'earnings':      earnings,
            'invoice_total': round(sum(i['due_amount'] for i in invoices), 2),
        }
