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
python3 -m studio.bookkeeper add-rule --match "strand book" --account "Expenses:Books"
python3 -m studio.bookkeeper pull   --source wise --from 2026-08-05 --commit
```

| Flag | Meaning |
|---|---|
| `--source` | `wise` (API), `wise-csv`, `harvest` (API), `bbva`, `upwork`, `stripe` |
| `--file` | CSV to import (required for every source but `wise`) |
| `--from` / `--to` | Date range for an API pull |
| `--profile` | `business` or `personal`; both if omitted |
| `--account` | Override the target account path |
| `--rules` | Rules file (defaults to `FINANCE_CONFIG_DIR/bookkeeper-rules.yaml`) |
| `--book` | Book path (defaults to `GNUCASH_FILE`) |
| `--out` | Write the review sheet to a file instead of stdout |
| `--date-tolerance` | Days either side to treat a same-amount entry as a possible duplicate (default 3; 0 = exact dates only) |
| `--commit` | Actually write. **Dry run is the default.** |

## Where rules stop and judgement starts

Measured over 377 real transactions across both Wise profiles:

| | merchants | share of volume |
|---|---|---|
| Seen 3+ times | 32 | **74.8%** |
| Seen twice | 12 | 6.4% |
| Seen once | 71 | **18.8%** |

Three quarters of volume is a few dozen recurring suppliers whose treatment never
changes. Rules own that outright: zero marginal cost, and the same merchant classifies
identically every quarter, which is what makes a re-run reproducible and a filing
defensible.

The long tail is different. Naming 71 one-off merchants in a rules file is the
brittleness the file should avoid, so it isn't done. Two mechanisms cover it instead:

- **`fallbacks:`** — conditional defaults scoped by currency, direction, date window,
  source account or amount, never by merchant. One entry replaces an enumeration.
- **the skill** — decides genuinely novel cases, then records the answer with
  `add-rule` so that merchant is settled from then on.

The rules file is therefore a **cache of decisions**, not a hand-maintained document.
Nobody writes rules by hand; the skill promotes them as they are confirmed.

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
(scope to one bank account), a `csv_profiles:` block overriding a provisional column map,
and `wise_accounts:` for renamed accounts.

### Fallbacks

Tried in order, only when no named rule matches:

```yaml
fallbacks:
  - when:
      currency: USD
      direction: out
      from: 2026-07-21
      to: 2026-09-08
      account_contains: "Wise Business"
    account: "Assets:Future Assets:Money Owed To BD:Personal Debt:Alba USA"
    reason: "USD card spend on the business account during Alba's US trip"
    confident: true        # omit and it still classifies, but asks first
```

`when:` also accepts `max_amount:`, which is how the review threshold is set. Personal
spending from the personal Wise account books itself below 50 and is classified-but-flagged
above it — two fallbacks, the bounded one first.

The threshold exists because the risk is asymmetric. Personal spending mis-booked as a
business expense overstates the Modelo 303 deduction, which is the direction with
consequences; a business expense mis-booked as Personal Debt merely understates it. The
fallback errs the safe way, and real suppliers recur often enough to earn a named rule.

### Adding a rule

```bash
python3 -m studio.bookkeeper add-rule --match "strand book" --account "Expenses:Books" \
    [--currency USD] [--direction out] [--from 2026-07-21] [--to 2026-09-08] [--note "why"]
```

Appends to the `rules:` block by text insertion, so the file's comments survive — a YAML
round-trip would strip them. Refuses a merchant that already has a rule, and refuses to
save a file it cannot parse back.

## Status

| Source | Column map | Notes |
|---|---|---|
| Wise API | n/a | Uses `~/.config/wise/wise_client.py`, shared with wise-pulse |
| Harvest API | n/a | Invoices, via the dashboard's `harvest_client.py` |
| Wise CSV | VERIFIED | Checked against real business and personal exports |
| BBVA | VERIFIED | .xlsx, sheet "Informe BBVA", headers row 5, dates dd/mm/yyyy from `Fecha` |
| Upwork | VERIFIED | Drops scheduled rows — future-dated, no running balance |
| Stripe | PROVISIONAL | Not yet seen a real export — verify before `--commit` |

## Invoices, and why they need their own source

Every other source reads a bank feed: money that has already moved. `harvest` reads
invoices, which is when income is *recognised*, and that happens first:

```
issue    DR Accounts Receivable (CCY)   CR Income:Client Income (CCY)
payment  DR Bank                        CR Accounts Receivable (CCY)
```

The bank adapters only ever book the second line. **A client payment arriving must clear a
receivable, never create income** — mapping one to Client Income counts the same revenue
twice and inflates the Modelo 303 base.

Both halves have to run, or Accounts Receivable drifts. A missing invoice drives it
negative, which is the signal to look: on 2026-09-08 it read −1,000.00, and Harvest showed
two invoices issued 2026-08-31 that had never been booked.

State is ignored deliberately — an invoice is income in the quarter it was *issued*,
whether or not it has been paid. That is the accrual basis the tax-prep skill works on.

```bash
python3 -m studio.bookkeeper pull --source harvest --from 2026-07-01 --to 2026-09-30
```

## The personal-to-business transition

Business spending is moving from the personal Wise account to the business one, starting
**2026-03-05** (first transaction on the business profile). During the overlap the same
merchant appears on both, which needs no special handling: both accounts are in the book,
so a business expense books as an expense whichever account paid it, via its named rule.

What differs is the leftovers. Personal spending out of an account that also holds business
money is a debt back to the business, so `Wise Main` has a fallback routing unmatched
outgoings to `Money Owed To BD:Personal Debt`. It is deliberately **not** `confident`:
while the transition runs, an unmatched merchant on that account is as likely to be a new
supplier as a shop, so it is classified and flagged rather than assumed. Promote the real
suppliers to named rules with `add-rule` as they appear.

The statement's profile is whatever `--profile` says, and that is trusted outright — a
transfer between the two profiles carries both names on the same row, so inferring from
either one books the money against the wrong account.

## Personal spending

`Equity ("Capital"):Owner's Draw` is **EUR only, by design** — it takes the monthly draw from
BBVA and nothing else. Card spending never belongs in it, in any currency.

Personal spending on a business card is a debt back to the business and books to
`Assets:Future Assets:Money Owed To BD:Personal Debt`, whose per-currency leaf the resolver
picks. A specific, bounded debt gets its own sub-account so the balance owed for that one
thing stays legible — Alba's 2026 US trip books to `Alba USA`, matched by date- and
currency-scoped rules sitting above the general ones (window `2026-07-21` to `2026-09-08`,
now closed).

Close a named debt's window when the event ends, or later spending of the same shape gets
misattributed to it.

The Aletheia Codex, section 2 ("Personal Spending on Business Accounts"), is authoritative
for this treatment; the rules file just implements it.

Known gap: `Income:Other Income` exists in EUR only, so USD/GBP cashback is held until the
leaves are created in GnuCash.
