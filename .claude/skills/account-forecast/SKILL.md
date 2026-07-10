---
name: account-forecast
description: Per-account forecast of upcoming transactions with running balance and insufficient-funds flags. Shows what comes off which account and when. Run before scheduling payments, or any time you need to check whether a specific account can cover what's coming.
allowed-tools: [Read, Write, Bash]
---

# Account Forecast

A ledger-level view, not a business one: for each bank account, what's about to come off it, in what order, and whether the balance goes negative before it recovers.

## Steps

### 0. Load business context

Read `{CONTENT_DIR}/finance/aletheia-codex.md` before anything else. It's the authoritative record of account topology and which obligations draw from which account.

### 1. Read the financial snapshot

Read `{CONTENT_DIR}/finance/accounts.json`. If more than 24 hours old, run `python3 studio/collectors/gnucash_collector.py` to refresh.

Key fields:
- `bank_balances` — current balance per account
- `upcoming_all` — every predicted transaction, each with `date`, `label`, `amount`, `type` (`fixed`, `tax`, `draw`, `income`, ...), and `account`

### 2. Split unattributed transactions

Some recurring items in `upcoming_all` have `account: "Unknown"` — the source data doesn't yet say which account they draw from. Pull these into a separate "unassigned" list and call them out explicitly. Don't guess which account they belong to and don't fold them into any account's running balance — a wrong guess is worse than an honest gap.

### 3. Group and project, per account

For each named account (not "Unknown"):
- Start from its current balance (`bank_balances`).
- Sort its transactions from `upcoming_all` by date, ascending.
- Walk forward: income/inflow types add to the running balance, everything else subtracts.
- Record the running balance after each transaction.

### 4. Flag insufficient funds

Any point where an account's running balance goes negative is a flag. For each flagged account, report:
- The date it first goes negative
- The transaction that tips it over
- The shortfall amount (how far negative)
- Whether it recovers later in the window (and when)

### 5. Output

Lead with a one-line summary: which accounts (if any) run short, and by when. This is the part that actually matters — put it first, not buried in tables.

Then, per account, a table:

| Date | Label | Type | Amount | Running balance |
|---|---|---|---|---|

Mark the row where balance goes negative clearly (e.g. `⚠ SHORTFALL`).

Close with the unassigned-transactions list from step 2, if any, so nothing silently falls through the cracks.

Be direct. If an account is going to run short, say so plainly and say when.
