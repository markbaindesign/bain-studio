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

from .book import Book, default_book_path
from .categorise import Rules
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


def main(argv=None):
    parser = argparse.ArgumentParser(prog="bookkeeper")
    parser.add_argument("command",
                        choices=["pull", "import", "accounts", "add-rule",
                                 "journal"],
                        help="pull = fetch from an API; import = read a file; "
                             "add-rule = record a confirmed classification; "
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
                        help="journal: 'Account path|amount|CCY', repeatable. "
                             "Amounts must net to zero per currency.")
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

    if args.command == "accounts":
        for path in sorted(book.by_path):
            acc = book.by_path[path]
            if acc.type in ("BANK", "CASH", "CREDIT", "ASSET", "LIABILITY"):
                print("%-10s %-4s %s" % (acc.type, acc.currency, path))
        return 0

    if args.command == "add-rule":
        if not args.match or not args.account:
            raise SystemExit("add-rule needs --match and --account")
        try:
            added = append_rule(
                rules.path, args.match, args.account, currency=args.currency,
                direction=args.direction, date_from=args.start, date_to=args.end,
                note=args.note, account_contains=args.account_contains,
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
            if len(parts) != 3:
                raise SystemExit("Bad --leg %r: expected 'Account|amount|CCY'" % spec)
            txn.legs.append(Leg(parts[0], parts[1], parts[2].upper()))
        txn.balanced_by_construction = True
        if not txn.is_balanced():
            raise SystemExit(
                "The legs do not net to zero — a journal entry must balance."
            )
        txns = [txn]
    else:
        txns = gather(args, rules)
    print("  %d transactions read from %s" % (len(txns), args.source))

    result = run(txns, book, rules, args.date_tolerance)
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
