"""The pipeline: normalise, dedupe, categorise, report, commit."""

from collections import defaultdict
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Dict, List

from .book import Book
from .categorise import Rules, categorise, resolve_account
from .model import Txn


@dataclass
class Result:
    ready: List[Txn] = field(default_factory=list)
    review: List[Txn] = field(default_factory=list)
    duplicates: List[Txn] = field(default_factory=list)
    unbalanced: List[Txn] = field(default_factory=list)

    @property
    def counts(self) -> Dict[str, int]:
        return {
            "ready": len(self.ready),
            "review": len(self.review),
            "duplicates": len(self.duplicates),
            "unbalanced": len(self.unbalanced),
        }


def run(txns: List[Txn], book: Book, rules: Rules) -> Result:
    """Sort incoming transactions into ready / review / duplicate / unbalanced."""
    result = Result()

    for txn in sorted(txns, key=lambda t: (t.date, t.description)):
        if book.contains(txn):
            result.duplicates.append(txn)
            continue

        # Adapters name account families ("Expenses:Bank Fees"); the book keeps
        # per-currency leaves. Resolve those before the contra leg is sized.
        # A family name can itself exist as a placeholder parent in another
        # currency, so an existing path is not on its own proof of a fit —
        # check the currency too, or a USD fee posts to the EUR parent.
        unresolved = []
        for leg in txn.legs[1:]:
            existing = book.account(leg.account)
            if existing is not None and existing.currency == leg.currency:
                continue
            resolved = resolve_account(book, leg.account, leg.currency)
            if resolved:
                leg.account = resolved
            else:
                unresolved.append("%s (%s)" % (leg.account, leg.currency))

        if unresolved:
            txn.needs_review = True
            txn.review_reason = (
                "No account for %s — create it in GnuCash first"
                % ", ".join(unresolved)
            )
            result.review.append(txn)
            continue

        categorise(txn, rules, book)

        if txn.needs_review:
            result.review.append(txn)
            continue

        if not txn.is_balanced():
            txn.review_reason = "Legs do not net to zero"
            result.unbalanced.append(txn)
            continue

        result.ready.append(txn)

    return result


def summarise(result: Result) -> Dict[str, Dict[str, float]]:
    """Net movement per account across the ready transactions."""
    totals: Dict[str, Dict[str, Fraction]] = defaultdict(lambda: defaultdict(Fraction))
    for txn in result.ready:
        for leg in txn.legs:
            totals[leg.account][leg.currency] += leg.amount
    return {
        account: {ccy: float(amount) for ccy, amount in by_ccy.items()}
        for account, by_ccy in totals.items()
    }


def review_sheet(result: Result) -> str:
    """A markdown sheet of everything a human needs to decide on."""
    lines = ["# Bookkeeper review", ""]
    counts = result.counts
    lines.append(
        "ready: %d | needs review: %d | already in book: %d | unbalanced: %d"
        % (counts["ready"], counts["review"], counts["duplicates"], counts["unbalanced"])
    )
    lines.append("")

    if result.review:
        lines += ["## Needs a rule", "",
                  "Add a matching entry to the rules file, then re-run.", "",
                  "| Date | Description | Amount | Account | Why |",
                  "|---|---|---|---|---|"]
        for txn in result.review:
            leg = txn.primary
            lines.append(
                "| %s | %s | %.2f %s | %s | %s |"
                % (txn.date, txn.description.replace("|", "/"), float(leg.amount),
                   leg.currency, leg.account.split(":")[-1], txn.review_reason)
            )
        lines.append("")

    if result.unbalanced:
        lines += ["## Does not balance", "",
                  "| Date | Description | Legs |", "|---|---|---|"]
        for txn in result.unbalanced:
            legs = "; ".join(
                "%s %.2f %s" % (l.account.split(":")[-1], float(l.amount), l.currency)
                for l in txn.legs
            )
            lines.append("| %s | %s | %s |" % (txn.date, txn.description, legs))
        lines.append("")

    if result.ready:
        lines += ["## Ready to write", "",
                  "| Date | Description | Amount | Posting |", "|---|---|---|---|"]
        for txn in result.ready:
            leg = txn.primary
            contra = "; ".join(l.account for l in txn.legs[1:]) or "(none)"
            lines.append(
                "| %s | %s | %.2f %s | %s |"
                % (txn.date, txn.description.replace("|", "/"), float(leg.amount),
                   leg.currency, contra)
            )
        lines.append("")

    return "\n".join(lines)
