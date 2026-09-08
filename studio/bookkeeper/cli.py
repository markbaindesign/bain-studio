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
from .sources import csv_source, wise
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

    if args.source == "wise-csv":
        if not args.file:
            raise SystemExit("--file is required for wise-csv")
        return wise.from_csv(args.file, accounts, args.profile or "personal")

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
    parser.add_argument("command", choices=["pull", "import", "accounts"],
                        help="pull = fetch from an API; import = read a file")
    parser.add_argument("--source", default="wise",
                        help="wise, wise-csv, bbva, upwork, stripe")
    parser.add_argument("--file", help="path to a CSV export")
    parser.add_argument("--from", dest="start", help="start date (YYYY-MM-DD)")
    parser.add_argument("--to", dest="end", help="end date (YYYY-MM-DD)")
    parser.add_argument("--profile", choices=["business", "personal"],
                        help="Wise profile; both if omitted")
    parser.add_argument("--account", help="override the target account path")
    parser.add_argument("--book", help="path to the .gnucash book")
    parser.add_argument("--rules", help="path to the rules YAML")
    parser.add_argument("--out", help="write the review sheet to this path")
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

    txns = gather(args, rules)
    print("  %d transactions read from %s" % (len(txns), args.source))

    result = run(txns, book, rules)
    counts = result.counts
    print("  ready: %(ready)d | needs review: %(review)d | "
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
