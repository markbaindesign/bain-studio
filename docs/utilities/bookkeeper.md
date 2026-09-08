---
tags: [utility, finance, gnucash, bookkeeping]
god: financial-review
command: python3 -m studio.bookkeeper
invoke: /bookkeeper
description: Catch the GnuCash books up from bank feeds — pulls Wise via API, imports CSV exports, dedupes, restores netted-out fees, and writes balanced transactions.
---

# Bookkeeper

Input: bank statements and API calls. Output: balanced books.

Replaces the manual loop of downloading a statement per account per currency, deduping by
eye, restoring the fee the provider nets out of every line, and typing it all into GnuCash.

See **ADR 015** for why this writes the book directly, and the **GnuCash Transaction
Playbook** (sections 3 and 4) for the accounting treatment it implements.

## Usage

```bash
python3 -m studio.bookkeeper accounts                              # what's in the book
python3 -m studio.bookkeeper pull   --source wise --from 2026-08-05
python3 -m studio.bookkeeper import --source wise-csv --file x.csv --profile business
python3 -m studio.bookkeeper pull   --source wise --from 2026-08-05 --commit
```

| Flag | Meaning |
|---|---|
| `--source` | `wise` (API), `wise-csv`, `bbva`, `upwork`, `stripe` |
| `--file` | CSV to import (required for every source but `wise`) |
| `--from` / `--to` | Date range for an API pull |
| `--profile` | `business` or `personal`; both if omitted |
| `--account` | Override the target account path |
| `--rules` | Rules file (defaults to `FINANCE_CONFIG_DIR/bookkeeper-rules.yaml`) |
| `--book` | Book path (defaults to `GNUCASH_FILE`) |
| `--out` | Write the review sheet to a file instead of stdout |
| `--date-tolerance` | Days either side to treat a same-amount entry as a possible duplicate (default 3; 0 = exact dates only) |
| `--commit` | Actually write. **Dry run is the default.** |

## How it works

```
source adapter -> normalise -> dedupe -> resolve accounts -> categorise -> verify -> write
```

- **Adapters** (`sources/`) turn one provider's export into `Txn` objects. Wise has a
  dedicated adapter because its API and CSV share a format; everything else uses the
  generic `csv_source` driven by a `ColumnMap`, so a new bank is a dozen lines, not a
  module.
- **Dedupe** matches on date, account, amount and currency — deliberately not description,
  because banks reword the same transaction between exports. A same-amount entry within
  `--date-tolerance` days (default 3) is reported as a **possible duplicate** and held, not
  written: hand entries are routinely dated the day they were typed rather than the day the
  bank settled, and exact-date matching sails straight past those. Matching is one-to-one,
  so three identical fares in the book absorb at most three incoming rows.
- **Fees.** Providers report the amount *net* of their charge; the real movement is that
  figure plus the fee. A $1,000 inbound transfer with a $6.11 fee appears as $993.89 and is
  written as bank +993.89, charges +6.11, income −1,000.00.
- **Account resolution.** The book keeps per-currency leaves
  (`Expenses:Bank Fees:Bank Fees (USD)`). Rules name a *family* and the currency picks the
  leaf. No leaf in the needed currency means the line is held, never posted to a mismatched
  one.
- **Trading accounts.** The book has them enabled, so a cross-currency transaction gets a
  trading leg per real leg. Without those GnuCash reports an imbalance.

## Safety

Four guarantees, all covered by `studio/tests/test_bookkeeper.py`:

1. Dry run by default; `--commit` is the only thing that writes.
2. A timestamped backup lands in `Backups/` before the file is touched.
3. Balances are predicted before the write and re-derived from disk after; a mismatch
   restores the backup.
4. A `.LCK` file (GnuCash has the book open) refuses the write outright — otherwise the app
   would overwrite it on its next save.

Anything unclassified is **held back**, not guessed. A wrong expense account still balances,
so it raises no error; it just distorts the next Modelo 303 quietly.

## Rules file

`$FINANCE_CONFIG_DIR/bookkeeper-rules.yaml` — outside this repo, because the merchant list
is personal spending data and this repo is public.

```yaml
rules:
  - match: "cloudways"                       # substring, case-insensitive
    account: "Expenses:Online Services:Hosting"
  - match: "khyentse foundation"
    account: "Income:Client Income"
    direction: in                            # only when money comes in
  - match: "trader joe"                      # date- and currency-scoped
    account: "Assets:Future Assets:Money Owed To BD:Personal Debt:Alba USA"
    from: 2026-07-21
    currency: USD
  - match: "amazon"
    account: "Expenses:Computer"
    review: true                             # post, but always ask
    review_reason: "confirm business or personal"
```

Also accepts `regex: true`, `from:`/`to:` (date window), `currency:`, `account_contains:`
(scope to one bank account), a
`csv_profiles:` block overriding a provisional column map, and `wise_accounts:` for renamed
accounts.

## Status

| Source | Column map | Notes |
|---|---|---|
| Wise API | n/a | Uses `~/.config/wise/wise_client.py`, shared with wise-pulse |
| Wise CSV | VERIFIED | Checked against real business and personal exports |
| BBVA | PROVISIONAL | Not yet seen a real export — verify before `--commit` |
| Upwork | PROVISIONAL | " |
| Stripe | PROVISIONAL | " |

## Personal spending

`Equity ("Capital"):Owner's Draw` is **EUR only, by design** — it takes the monthly draw from
BBVA and nothing else. Card spending never belongs in it, in any currency.

Personal spending on a business card is a debt back to the business and books to
`Assets:Future Assets:Money Owed To BD:Personal Debt`, whose per-currency leaf the resolver
picks. Spending on Alba's US trip (from 2026-07-21) has its own account, `Alba USA`, and is
matched by date- and currency-scoped rules sitting above the general ones.

Set a `to:` date on those rules once the trip ends, or the open window will keep claiming
later US spending as hers.

Known gap: `Income:Other Income` exists in EUR only, so USD/GBP cashback is held until the
leaves are created in GnuCash.
