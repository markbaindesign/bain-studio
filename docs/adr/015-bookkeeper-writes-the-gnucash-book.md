# ADR 015 — The bookkeeper writes the GnuCash book directly

Date: 2026-09-08
Status: Accepted

## Context

`Admin/Financial/Accounting/CLAUDE.md` has said since it was written: *"this directory
holds the data file, not a GnuCash installation - actual entry/editing of transactions
happens in the GnuCash app itself. Don't hand-edit the `.gnucash` XML."* That was the right
rule when the only thing reading the book was `gnucash_parser.py`, which never writes.

Catching the books up is now the largest recurring manual task in the studio. As of
2026-09-08 the book was current only to 25 August across eleven separate feeds, with Stripe
a full quarter behind, and the Q3 Modelo 303/130/111 filing due 20 October depends on it
being complete. The manual loop is: download a statement per account per currency, dedupe
by eye against what is already entered, restore the fee Wise nets out of every line, decide
an account for each merchant, and type it in.

Everything in that loop except the last step is deterministic. The studio's standing
preference is deterministic scripting over skills, so the work belongs in a script - and a
script that stops one step short of writing still leaves the slowest, most error-prone part
(manual transcription into GnuCash) in place, along with the import-mapping dialog that has
to be re-driven per file.

The alternative considered was emitting import-ready CSV per currency account and letting
GnuCash's importer do the write. That preserves the existing rule but keeps a manual step
per account per run - six files for Wise alone - and GnuCash's CSV importer cannot express
the trading-account legs a cross-currency transaction needs.

## Decision

`studio/bookkeeper` may write transactions into the book, under four constraints. The rule
in the Accounting `CLAUDE.md` is amended to prohibit *ad hoc* hand-editing of the XML, while
permitting writes through this one audited tool.

1. **Dry run is the default.** Nothing is written without an explicit `--commit`.
2. **Back up first.** A timestamped copy goes to `Backups/` before the file is touched, and
   is restored automatically if verification fails.
3. **Verify after.** Every affected account's balance is predicted before the write, then
   re-derived from the file on disk afterwards. Any discrepancy rolls back.
4. **Refuse when GnuCash holds the book.** A `.LCK` file means the app is open and would
   overwrite the write on its next save.

Anything the rules file cannot classify is **held back**, not guessed. A transaction posted
to the wrong expense account still balances, so it produces no error - it just quietly
distorts the deduction claimed on the next Modelo 303. Absent is recoverable; wrong is not.

## Amendment, 2026-09-08 — where rules stop

The first cut classified everything by named merchant rules, and Mark pushed back that
this would be too brittle and belonged in a skill. Measuring 377 real transactions
settled it: 32 merchants account for 74.8% of volume, while 71 merchants appear exactly
once and account for 18.8%. The initial rules file was 60 rules, 25 of which were a
single concept ("USD spending during Alba's trip") enumerated shop by shop.

Both halves are real, so the boundary moved rather than the mechanism:

- **Recurring merchants stay rules.** Determinism is the point. The same merchant must
  classify identically every quarter, or a re-run of a filed quarter stops reproducing
  and the filing stops being defensible. An LLM re-deciding "Cloudways is hosting" every
  month adds variance where variance is least acceptable.
- **The long tail moves to the skill**, backed by `fallbacks:` — conditional defaults
  scoped by currency, direction, date window, account or amount, never by merchant. The
  25 Alba rules became one fallback with identical output.
- **The skill's decisions are written back as rules** via `add-rule`. The rules file is
  a cache of decisions, not a hand-maintained document, so the review queue shrinks with
  every run and nothing is decided twice.

The arithmetic layer was never in question and does not move. Fee restoration, dedupe,
trading legs and balance verification stay deterministic; both real errors caught during
development (a netted-out fee, seven date-drift duplicates) came from that layer, and
neither was visible by eye.

## Consequences

- The book is no longer only ever written by GnuCash, so a corrupt write is now a way the
  books can break. Mitigated by the four constraints above, the test suite
  (`studio/tests/test_bookkeeper.py`), and the fact that every run leaves a restorable
  backup.
- The merchant rules file holds personal spending detail, so it lives in
  `Accounting/config/bookkeeper-rules.yaml`, not in this public repo.
- The book uses trading accounts (`Trading:CURRENCY:*`). Any cross-currency transaction must
  carry a trading leg per real leg or GnuCash reports an imbalance; the writer does this,
  and it is the main reason the CSV-import alternative was rejected.
- The book keeps per-currency leaf accounts (`Expenses:Bank Fees:Bank Fees (USD)`). Rules
  name an account *family* and the currency selects the leaf; where no leaf exists in the
  needed currency the line is held for review rather than posted to a mismatched one.
- Superseded manual guidance stays valid as the description of what the tool does: the
  GnuCash Transaction Playbook, section 3 (currency conversion with a bank fee) and section
  4 (Upwork withdrawals in transit), remain authoritative for the accounting treatment.
