---
name: bookkeeper
description: Catch the GnuCash books up from bank feeds — pulls Wise via API, imports CSV exports from BBVA/Upwork/Stripe, dedupes against the book, restores netted-out fees, and writes balanced transactions. Use when the books need updating, before a quarterly tax filing, or when asked to reconcile an account.
allowed-tools: [Bash, Read, Edit]
---

# Bookkeeper

Turns bank statements into balanced books. The deterministic work lives in
`studio/bookkeeper/` (see ADR 015); this skill drives it and handles the one part
that needs judgement — deciding what an unrecognised merchant is.

**Read first:** the GnuCash Transaction Playbook at
`/media/data/Dropbox/Work/Work Notes/Financial/Accounting/gnucash-playbook.md`
(section 3 for conversion fees, section 4 for Upwork suspense) and
`aletheia-codex.md` for account topology and IVA/IRPF treatment.

## Invoke

```bash
# Dry run — always do this first. Nothing is written.
python3 -m studio.bookkeeper pull --source wise --from 2026-08-05

# From a downloaded file
python3 -m studio.bookkeeper import --source wise-csv --file export.csv --profile business
python3 -m studio.bookkeeper import --source bbva --file movimientos.csv

# Write, once the dry run looks right
python3 -m studio.bookkeeper pull --source wise --from 2026-08-05 --commit

# List the accounts the book actually has
python3 -m studio.bookkeeper accounts
```

Sources: `wise` (API), `wise-csv`, `bbva`, `upwork`, `stripe`.
Flags: `--from/--to`, `--profile business|personal`, `--account`, `--out FILE`,
`--rules FILE`, `--book FILE`, `--commit`.

## Steps

1. **Check the book is closed.** A `.LCK` file next to `accounts.gnucash` means GnuCash
   is open; the tool refuses, and it is right to. Ask Mark to close it.
2. **Dry run** the source. Report the four counts: ready, needs review, already in book,
   unbalanced.
3. **Work the review list.** For each unmatched merchant, propose an account and ask Mark
   to confirm in one batch — never one question per line. Business-vs-personal is the
   judgement that matters most: spending on the business card that is not a business
   expense goes to Owner's Draw, not an expense account, or it inflates the Modelo 303
   deduction.
4. **Add confirmed decisions** to `Accounting/config/bookkeeper-rules.yaml` so the same
   merchant is never asked about twice. Rules name an account *family*
   (`Expenses:Software`); the currency picks the leaf.
5. **Re-run the dry run.** Repeat until the review list is only things that genuinely need
   a human.
6. **Commit** with `--commit`. Report what was written, the backup path, and the verified
   closing balances.
7. **Report what is still outstanding** — held-back lines, and any feed not yet pulled.

## Rules

- **Never invent an account.** If no account exists in the required currency, say so and
  ask Mark to create it in GnuCash. Do not substitute a near-miss.
- **Never post to Imbalance to make a run finish.** Held back is the correct outcome.
- **Never pass `--commit` on the first run** of a source whose column map is marked
  PROVISIONAL. Check the parsed rows against the raw file first.
- **Do not edit the `.gnucash` XML by hand**, ever. ADR 015 permits writes through this
  tool only.
- Amounts are exact fractions throughout. If you find yourself reaching for a float to
  fix a rounding complaint, something else is wrong.

## Known gaps

- `Owner's Draw` exists only in EUR. USD and GBP personal spending on the business card
  is held for review until those accounts are created.
- `Income:Other Income` is EUR-only, so USD/GBP cashback is held for the same reason.
- BBVA, Upwork and Stripe column maps are PROVISIONAL — unverified against a real export.
- Suspense (USD) carries a stale $340.74 from Dec 2025 / Jan 2026 that predates this tool.
