---
description: Forecast income in five tiers (receivable, unbilled, fixed, predicted, milestone) for every cash flow forecast
command: python3 studio/collectors/gnucash_collector.py
role: Finance
tags:
- utility
---

# Income Forecast

`studio/dashboard/income_forecast.py` is the single source of forecast income. `gnucash_parser.py` merges it into `upcoming`, and the collector writes that out as `accounts.json` `upcoming_all`. `/account-forecast`, the daily Slack forecast (`studio/scripts/account_forecast_report.py`) and the dashboard all read the same figures from there.

Before this module, recurring income was hard-coded in the Slack script only, so `/account-forecast` showed outgoings-only balances.

## Tiers

| Tier | Source | Meaning |
|---|---|---|
| `receivable` | GnuCash `Accounts Receivable` leaves | Invoices already sent and still open |
| `unbilled` | Harvest uninvoiced report, per project | Billable hours logged, not yet invoiced |
| `fixed` | `income.yaml` `recurring:` | Recurring, same amount each period |
| `predicted` | `income.yaml` `recurring:` | Recurring, amount varies period to period |
| `milestone` | `income.yaml` `milestones:` | Agreed project payments not yet invoiced |

Forecasts judge shortfalls on the **base case**: `receivable` + `unbilled` + `fixed`. Predicted income and milestones are reported as upside.

## Forecast window

Income and monthly bills share one window, `income_forecast.HORIZON_DAYS` (92 days), which matches the owner's draw projection. If income ran further out than outgoings, later months would look healthier than they are. Annual bills still show their next date, even when it falls beyond the window.

## Config: `FINANCE_CONFIG_DIR/income.yaml`

This file lives in Dropbox next to `recurring-transactions.yaml`, not in this repo, because it names clients and amounts.

- `receivables.clients` maps an AR transaction description (case-insensitive regex, `match`) to a landing account and `lag_days`, the days from invoice to cash. An unmatched open item still counts, under account `Unknown`. An overdue one is expected tomorrow.
- `recurring` entries take `label`, `match`, `tier` (`fixed` or `predicted`), `cadence` (`monthly` with `day`, or `weekly` with `weekday`, where 0 = Monday), `amount`, `currency`, `account`, `start` and an optional `end`.
- `milestones` entries take `label`, `match`, `date` (expected cash-in), `amount`, `currency` and `account`.

Amounts are what lands in the account: net of platform fees, in the account's currency.

**No double counting.** Once a period is invoiced, it is a receivable, so the recurring or milestone entry for it drops out. Entries are tied to their client's AR invoices (open or paid) by `match`, which uses the same string as the client's `receivables.clients` entry:

- **fixed:** skipped when an AR invoice of the same amount is dated within 10 days of when the occurrence would be invoiced (the occurrence date less the client's `lag_days`). The amount check stops a milestone invoice from hiding the retainer.
- **predicted:** the same, without the amount check.
- **milestone:** skipped when any AR invoice of the same amount exists.

`start` is only needed for periods invoiced before the config existed. An entry without `match` is never deduplicated, which is right for income that never goes through AR, such as Upwork.

A missing `income.yaml` raises an error rather than forecasting without income.

Aggregates (`income_30d`, `balance_after_30d`, the BBVA 30-day figure and the collector's month-end line) count base-case income only, via `income_forecast.is_base()`.

## Unbilled hours

Each billable, non-fixed-fee Harvest project with uninvoiced work becomes one entry. It is assumed to be invoiced at the end of the current month and paid after the client's `lag_days`, net of any `fee_pct`. The entry is matched to a client rule on `"Client | Project"`.

- Fixed-fee projects are skipped. Their payments are milestones.
- `unbilled.exclude` (regex on `"Client | Project"`) drops hours a recurring tier already pays for: the NORE Upwork contract, the Techstyle retainer, and KF's fixed monthly fee. A project paid by a recurring entry must be listed here, or it is counted twice.
- Once the hours are invoiced, Harvest stops reporting them as uninvoiced, and the invoice appears as a receivable after it is booked in GnuCash.
- Harvest data is passed to `gnucash_parser.parse(harvest_projects=...)` by the dashboard server and by the collector's direct path. If Harvest or its uninvoiced report fails, `income_sources_missing` lists `harvest`, and the Slack report says income is incomplete. A failure is never treated as zero.
- Spanish clients (e.g. Jaume Beato) are forecast at the uninvoiced base amount. The cash actually received is base + 21% IVA - 15% IRPF.

## How receivables are read

Open items are computed per AR leaf from split **quantity**, which is in the leaf's own currency. Split value is in the transaction's currency and gives wrong answers for cross-currency entries. Payments clear invoices first in, first out. A payment with nothing open yet, such as one sorted ahead of a same-day invoice, is held as credit, so open items always sum to the leaf balance.

Only invoices booked in GnuCash count. An invoice that is open in Harvest but not yet booked to AR is invisible to the forecast until it is booked.

## Tests

`studio/tests/test_income_forecast.py`
