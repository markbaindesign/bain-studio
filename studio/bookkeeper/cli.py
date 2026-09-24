"""Bookkeeper CLI.

    python3 -m studio.bookkeeper pull   --source wise --from 2026-08-05
    python3 -m studio.bookkeeper import --source wise-csv --file path.csv
    python3 -m studio.bookkeeper import --source bbva --file export.csv --commit

Dry run is the default. Nothing reaches the book without --commit.
"""

import argparse
import os
import sys
from datetime import date, timedelta

from . import ack
from .book import Book, default_book_path
from .categorise import Rules, check_rules
from .pipeline import review_sheet, run, summarise
from .sources import csv_source, harvest, wise
from .rulewriter import RuleExists, append_rule
from .writer import WriteRefused, commit


def _load_env():
    """Read studio/.env so GNUCASH_FILE and friends are available."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(here, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def gather(args, rules) -> list:
    """Fetch transactions from whichever source was asked for."""
    accounts = wise.account_map(rules)

    if args.source == "wise":
        start = args.start or (date.today() - timedelta(days=30)).isoformat()
        end = args.end or date.today().isoformat()
        txns = []
        profiles = [args.profile] if args.profile else ["business", "personal"]
        for profile in profiles:
            for currency in ("USD", "GBP", "EUR"):
                txns += wise.from_api(profile, currency, start, end, accounts)
        return txns

    if args.source == "harvest":
        start = args.start or (date.today() - timedelta(days=120)).isoformat()
        end = args.end or date.today().isoformat()
        return harvest.invoices(start, end)

    if args.source == "wise-csv":
        if not args.file:
            raise SystemExit("--file is required for wise-csv")
        return wise.from_csv(args.file, accounts, args.profile or "")

    spec = csv_source.profile(args.source, rules)
    if not args.file:
        raise SystemExit("--file is required for %s" % args.source)
    if spec.get("status") == "PROVISIONAL":
        print(
            "  note: the %s column map is provisional — it has not yet been "
            "checked against a real export. Verify the parsed rows below before "
            "committing." % args.source,
            file=sys.stderr,
        )
    return csv_source.parse(
        args.file, spec["colmap"], args.account or spec["account"], args.source
    )


def _warn_profile(args, rules, book, result, total):
    """Flag a --profile that looks wrong for this export.

    The Wise history is booked under one profile's accounts, so a mismatched
    --profile makes rows look new instead of already booked. Re-run the
    dedupe with the other choice and warn when it explains far more rows.
    """
    if args.source != "wise-csv" or not args.file or total < 10:
        return
    accounts = wise.account_map(rules)
    tried = args.profile or "inferred per row"
    alt_profile = "" if args.profile else "business"
    alt_label = "inferred per row" if args.profile else "business"
    alt = wise.from_csv(args.file, accounts, alt_profile)
    alt = [t for t in alt if (not args.start or str(t.date) >= args.start)
           and (not args.end or str(t.date) <= args.end)]
    alt_dups = run(alt, book, rules, args.date_tolerance).counts["duplicates"]
    mine = result.counts["duplicates"]
    if alt_dups >= 10 and alt_dups >= 3 * max(mine, 1):
        print("  warning: with profile %s, %d of %d rows are already in the "
              "book; with profile %s, only %d. The history may be booked "
              "under different accounts than this profile maps to. Check "
              "--profile." % (alt_label, alt_dups, total, tried, mine),
              file=sys.stderr)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="bookkeeper")
    parser.add_argument("command",
                        choices=["pull", "import", "accounts", "add-rule",
                                 "check-rules", "journal"],
                        help="pull = fetch from an API; import = read a file; "
                             "add-rule = record a confirmed classification; "
                             "check-rules = verify every rule resolves to a "
                             "real account; "
                             "journal = post an entry that has no bank line")
    parser.add_argument("--source", default="wise",
                        help="wise, wise-csv, harvest, bbva, upwork, stripe")
    parser.add_argument("--file", help="path to a CSV export")
    parser.add_argument("--from", dest="start", help="start date (YYYY-MM-DD)")
    parser.add_argument("--to", dest="end", help="end date (YYYY-MM-DD)")
    parser.add_argument("--profile", choices=["business", "personal"],
                        help="Wise profile; both if omitted")
    parser.add_argument("--account", help="override the target account path")
    parser.add_argument("--book", help="path to the .gnucash book")
    parser.add_argument("--rules", help="path to the rules YAML")
    parser.add_argument("--out", help="write the review sheet to this path")
    parser.add_argument("--date", help="journal: entry date (YYYY-MM-DD)")
    parser.add_argument("--description", help="journal: entry description")
    parser.add_argument("--leg", action="append", default=[],
                        help="journal: 'Account path|amount|CCY[|value]', "
                             "repeatable. Amounts must net to zero per currency. "
                             "`value` is the same movement in the TRANSACTION's "
                             "currency (that of the first leg) and is required "
                             "only on a leg that crosses currencies.")
    parser.add_argument("--type", dest="acct_type",
                        help="accounts: only these types, comma-separated "
                             "(BANK,EXPENSE,INCOME,...)")
    parser.add_argument("--verbose", action="store_true",
                        help="check-rules: also list rules that resolve for only "
                             "some currencies")
    parser.add_argument("--replace", action="store_true",
                        help="add-rule: overwrite an existing rule of the same scope")
    parser.add_argument("--acknowledge-duplicates", action="store_true",
                        help="record every possible duplicate in this run as "
                             "already in the book, so it stops being listed")
    parser.add_argument("--match", help="add-rule: merchant substring to match")
    parser.add_argument("--note", help="add-rule: comment to record above the rule")
    parser.add_argument("--direction", choices=["in", "out"],
                        help="add-rule: restrict to money in or out")
    parser.add_argument("--currency", help="add-rule: restrict to one currency")
    parser.add_argument("--account-contains", dest="account_contains",
                        help="add-rule: restrict to bank accounts whose path contains this")
    parser.add_argument("--date-tolerance", type=int, default=3,
                        help="days either side to treat a same-amount entry as a "
                             "possible duplicate (0 disables)")
    parser.add_argument("--commit", action="store_true",
                        help="actually write to the book (default is a dry run)")
    args = parser.parse_args(argv)

    _load_env()
    book_path = args.book or default_book_path()
    book = Book(book_path)
    rules = Rules.load(args.rules)

    if args.command in ("pull", "import"):
        broken, _ = check_rules(rules, book)
        for kind, label, target, ccys in broken:
            print("  warning: %s %r points at %s, which resolves in no book "
                  "account for %s. Run `check-rules`."
                  % (kind, label, target, "/".join(ccys) or "any currency"),
                  file=sys.stderr)

    if args.command == "accounts":
        wanted = {t.strip().upper() for t in args.acct_type.split(",")} \
            if args.acct_type else None
        for path in sorted(book.by_path):
            acc = book.by_path[path]
            if acc.type == "ROOT":
                continue
            if wanted and acc.type not in wanted:
                continue
            print("%-10s %-4s %s%s" % (acc.type, acc.currency, path,
                                       "  [placeholder]" if acc.has_children else ""))
        return 0

    if args.command == "check-rules":
        broken, partial = check_rules(rules, book)
        for kind, label, target, ccys in broken:
            print("  BROKEN  %s %r -> %s (no leaf for %s)"
                  % (kind, label, target, "/".join(ccys) or "any currency"))
        for kind, label, target, ok in (partial if args.verbose else []):
            print("  partial %s %r -> %s (resolves for %s only)"
                  % (kind, label, target, "/".join(ok)))
        print("  %d rules, %d fallbacks: %d broken, %d partial"
              % (len(rules.rules), len(rules.fallbacks), len(broken), len(partial)))
        return 1 if broken else 0

    if args.command == "add-rule":
        if not args.match or not args.account:
            raise SystemExit("add-rule needs --match and --account")
        try:
            added = append_rule(
                rules.path, args.match, args.account, currency=args.currency,
                direction=args.direction, date_from=args.start, date_to=args.end,
                note=args.note, account_contains=args.account_contains,
                replace=args.replace,
            )
        except RuleExists as exc:
            print("  %s" % exc, file=sys.stderr)
            return 1
        print("  added to %s:\n%s" % (rules.path, added.rstrip()))
        return 0

    if args.command == "journal":
        # Month-end accruals and other entries that never touch a bank feed.
        # Routed through the same pipeline as an import, so it inherits dedupe,
        # account resolution, balance verification and the backup.
        if not args.date or not args.description or len(args.leg) < 2:
            raise SystemExit(
                "journal needs --date, --description and at least two --leg "
                "arguments of the form 'Account path|amount|CCY'"
            )
        from datetime import datetime as _dt

        from .model import Leg, Txn
        txn = Txn(
            date=_dt.strptime(args.date, "%Y-%m-%d").date(),
            description=args.description,
            source="journal",
        )
        for spec in args.leg:
            parts = [p.strip() for p in spec.split("|")]
            if len(parts) not in (3, 4):
                raise SystemExit(
                    "Bad --leg %r: expected 'Account|amount|CCY[|value]'" % spec
                )
            txn.legs.append(Leg(
                parts[0], parts[1], parts[2].upper(),
                value=parts[3] if len(parts) == 4 else None,
            ))
        txn.balanced_by_construction = True
        if not txn.is_balanced():
            raise SystemExit(
                "The legs do not net to zero — a journal entry must balance."
            )
        txns = [txn]
    else:
        txns = gather(args, rules)
        # A file export is read whole whatever window was asked for (an Upwork
        # report is the entire history), so apply --from/--to here. Pulls are
        # windowed by the source already, and this is then a no-op.
        before = len(txns)
        if args.start:
            txns = [t for t in txns if str(t.date) >= args.start]
        if args.end:
            txns = [t for t in txns if str(t.date) <= args.end]
        if len(txns) != before:
            print("  %d rows outside %s..%s ignored"
                  % (before - len(txns), args.start or "start", args.end or "end"))
    print("  %d transactions read from %s" % (len(txns), args.source))

    ack_path = ack.default_ack_path(rules.path)
    acknowledged = ack.load(ack_path)
    result = run(txns, book, rules, args.date_tolerance, acknowledged)
    _warn_profile(args, rules, book, result, len(txns))
    if args.acknowledge_duplicates and result.possible_duplicates:
        added = ack.add(ack_path, [t.ack_key() for t in result.possible_duplicates])
        print("  acknowledged %d possible duplicate(s) as already in the book "
              "(%s)" % (added, ack_path))
    counts = result.counts
    print("  ready: %(ready)d | needs review: %(review)d | "
          "possible duplicates: %(possible_duplicates)d | "
          "already in book: %(duplicates)d | unbalanced: %(unbalanced)d" % counts)

    sheet = review_sheet(result)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(sheet)
        print("  review sheet: %s" % args.out)
    else:
        print()
        print(sheet)

    if not args.commit:
        print("\n  DRY RUN — nothing written. Re-run with --commit to write "
              "%d transactions." % counts["ready"])
        return 0

    if not result.ready:
        print("\n  Nothing ready to write.")
        return 0

    try:
        report = commit(book_path, result.ready, book)
    except WriteRefused as exc:
        print("\n  REFUSED: %s" % exc, file=sys.stderr)
        return 1

    print("\n  Written: %d transactions" % report["written"])
    print("  Backup:  %s" % report["backup"])
    print("  Verified balances:")
    for account, balance in sorted(report["balances"].items()):
        print("    %-60s %12.2f" % (account, balance))

    if result.review:
        print("\n  %d transactions still need a rule — see the review sheet."
              % len(result.review))
    return 0


if __name__ == "__main__":
    sys.exit(main())
