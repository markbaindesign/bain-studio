---
name: bookkeeper
description: Catch the GnuCash books up from bank feeds — pulls Wise via API, imports CSV exports from BBVA/Upwork, dedupes against the book, restores netted-out fees, and writes balanced transactions. Use when the books need updating, before a quarterly tax filing, or when asked to reconcile an account.
allowed-tools: [Bash, Read, Edit]
---

# Bookkeeper

Turns bank statements into balanced books.

The division of labour matters and is not negotiable (ADR 015):

- **The script owns arithmetic and the book.** Parsing, fee restoration, dedupe,
  trading legs, balance verification, the write itself. Never do this reasoning in
  your head — it has caught real errors that looked fine by eye.
- **You own the long tail.** Roughly 75% of transactions are recurring merchants
  already covered by rules. The remaining ~19% are merchants seen exactly once, and
  deciding what those are is the job rules can't do.
- **Your decisions become rules.** Every classification you make is written back via
  `add-rule`, so that merchant is settled forever and the review queue shrinks each
  run. You are not a categoriser that runs every time; you are how the rules file
  learns.

**Read first:** the Aletheia Codex (`Accounting/aletheia-codex.md`) — section 1 for
account topology, section 2 for personal spending vs Owner's Draw, sections 4-5 for
IVA/IRPF. And the GnuCash Transaction Playbook (`Work Notes/Financial/Accounting/
gnucash-playbook.md`) — section 3 for conversion fees, section 4 for Upwork suspense.

## Invoke

```bash
python3 -m studio.bookkeeper accounts [--type EXPENSE]               # what exists (all types)
python3 -m studio.bookkeeper check-rules                             # rules -> real accounts
python3 -m studio.bookkeeper pull   --source wise --from 2026-08-05  # dry run
python3 -m studio.bookkeeper import --source wise-csv --file x.csv --profile business
python3 -m studio.bookkeeper add-rule --match "strand book" --account "Expenses:Books"
python3 -m studio.bookkeeper pull   --source wise --from 2026-08-05 --commit
```

`--from`/`--to` filter file imports too, so pass the window rather than trimming the CSV.

Sources: `wise` (API), `wise-csv`, `bbva`, `upwork`, `harvest` (invoices). The feeds that
can fall behind, and so the only ones to check for "books are current", are Wise, BBVA and
Upwork. Stripe and PayPal are barely used: `stripe` still imports for the rare charge, but
never list either as a feed to chase or as outstanding work.

## Steps

1. **Check the book is closed.** A `.LCK` beside `accounts.gnucash` means GnuCash has
   it open; the tool refuses and is right to. Ask Mark to close it.
2. **Dry run.** Report the five counts: ready, needs review, possible duplicates,
   already in book, unbalanced.
3. **Work the possible-duplicates list first.** These are same-amount entries a few
   days either side of one already booked — nearly always the same transaction
   hand-entered on a different date. Check each against the book before assuming it
   is new. Getting this wrong double-counts income. Once confirmed as already
   booked, re-run with `--acknowledge-duplicates` so they are not listed again.
4. **Work the review queue.** For each unmatched merchant, propose an account **with
   your reasoning**, and ask Mark to confirm in **one batch** — never one question per
   line. State what you inferred from: currency, date, amount, what else was happening
   that week, whether it looks like a supplier or a shop.
5. **Record every confirmed decision** with `add-rule` (`--replace` to change one). Never hand-edit the YAML.
   Add `--currency` / `--direction` / `--from` / `--to` when the answer is only true
   in a given scope.
6. **Consider a fallback instead of a rule.** If you are about to add three or more
   rules that share a reason ("all of these are her trip"), that is one `fallbacks:`
   entry, not three rules. Say so and propose it — the whole point of that block is to
   stop the file becoming an enumeration of shops.
7. **Re-run the dry run** until review holds only things that genuinely need Mark.
8. **Commit** with `--commit`. Report what was written, the backup path, and the
   verified closing balances.
9. **Report what is still outstanding** — held-back lines, feeds not yet pulled.

## Rules

- **Never invent an account.** If none exists in the required currency, say so and ask
  Mark to create it in GnuCash. Do not substitute a near-miss.
- **Never post to Imbalance** to make a run finish. Held back is a correct outcome.
- **Never pass `--commit` on the first run** of a source whose column map is marked
  PROVISIONAL. Check the parsed rows against the raw file first.
- **Never edit the `.gnucash` XML.** ADR 015 permits writes through this tool only.
- **Business vs personal is the judgement that matters most.** Personal spending on a
  business card is a debt to the business (`Money Owed To BD`), never an expense, or
  it inflates the Modelo 303 deduction. Owner's Draw is EUR-only and takes the monthly
  BBVA draw and nothing else.
- Amounts are exact fractions. If you reach for a float to settle a rounding
  complaint, something else is wrong.

## Worked example: a multi-currency journal

`journal` handles a split with conversion and fees. A leg that crosses currencies takes
a fourth field, the same movement in the first leg's currency (signed like the leg;
add a separate fee leg if the conversion cost anything):

```bash
python3 -m studio.bookkeeper journal --date 2026-09-10 --description "USD to EUR" \
    --leg "Assets:Current Assets:Wise:Wise (Business):Wise Business (EUR)|920.00|EUR" \
    --leg "Assets:Current Assets:Wise:Wise (Business):Wise Business (USD)|-1000.00|USD|-920.00"
```

Dry-run first; the balance check and backup apply as for any import.

## Harvest invoices

`--source harvest` books income on issue. A Spanish invoice is split four ways: `Dr AR`
(amount due), `Dr IRPF Retenido`, `Cr Client Income` (pre-tax subtotal), `Cr IVA
Repercutido`. An invoice with no tax stays two legs. Check the dry run's Posting column
against the invoice before `--commit`.

## Amending something already booked

`studio.bookkeeper.amend` corrects splits that are already in the book. It is narrow on
purpose: transaction and split are named by GUID, nothing is searched for, and it will
not add or remove a transaction.

**Before repointing or restating any split, list every other split on that account
around the same date.** Entries are often booked as a *pass-through pair* — money routed
through Funds Upwork or a suspense account and straight out again — and the two halves
net to zero. Changing one half in isolation breaks the pair silently: the transaction
still balances, so nothing errors, but an account is left holding a residue and the
expense gets counted twice. This happened on 2025-10-20 and was caught only because a
platform balance came out negative, which is impossible.

Sanity-check the resulting balances against reality, not just against zero: an asset
account that cannot go negative, a suspense account that should sit at zero between
uses, a liability that should clear each month.

Always run it against a copy of the book first.

## Known gaps

- `Income:Other Income` is EUR-only, so USD/GBP cashback is held until those leaves
  exist.
- BBVA and Upwork column maps are VERIFIED against real exports.
- The Wise **personal** profile is treated as business (same rules as Wise Business), and
  the history is booked under the Personal accounts. Omit `--profile` on a `wise-csv`
  import unless you know the export's profile; the tool warns on a mismatch.
- Suspense (USD) carries a stale $340.74 from Dec 2025 / Jan 2026, predating this tool.
