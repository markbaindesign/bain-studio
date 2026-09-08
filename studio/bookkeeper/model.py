"""Normalised transaction model shared by every source adapter.

Every adapter converts its own export format into a list of `Txn`. Nothing
downstream (dedupe, categorise, write) knows or cares where a Txn came from.

Money is held as `Fraction` throughout — never float. GnuCash stores amounts as
exact rationals (`12345/100`) and a float round-trip is enough to put a
transaction a cent out and leave the book unbalanced.
"""

from dataclasses import dataclass, field
from datetime import date
from fractions import Fraction
from typing import Optional, List


CENTS = 100


def to_fraction(value) -> Fraction:
    """Parse a money value into an exact Fraction.

    Accepts str, int, float, Fraction or Decimal. Floats are routed through
    str() so that 4.65 becomes 465/100 rather than the binary approximation.
    """
    if isinstance(value, Fraction):
        return value
    if value is None or value == "":
        return Fraction(0)
    return Fraction(str(value).strip().replace(",", ""))


def as_gnc_numeric(value: Fraction, denom: int = CENTS) -> str:
    """Render a Fraction as GnuCash's ``numerator/denominator`` string."""
    scaled = value * denom
    if scaled.denominator != 1:
        # Round half-up to the smallest unit; a sub-cent residue can only come
        # from an FX calculation and must not silently unbalance the split.
        scaled = Fraction(int(scaled + Fraction(1, 2)) if scaled >= 0
                          else -int(-scaled + Fraction(1, 2)), 1)
    return "%d/%d" % (scaled.numerator, denom)


@dataclass
class Leg:
    """One side of a transaction: an amount landing in one account.

    `amount` is in `currency`, which is the currency of the account the leg
    posts to. Cross-currency transactions carry legs in different currencies;
    the writer adds the trading-account legs that make them balance.
    """

    account: str          # full colon-delimited account path
    amount: Fraction      # positive = into the account, negative = out
    currency: str

    # The same movement expressed in the *transaction's* currency. Only needed
    # when this leg's currency differs from the transaction's — a conversion,
    # or a card payment billed in another currency. The source adapter knows
    # both sides of such a transaction and sets this; everything else leaves it
    # None and the writer treats it as equal to `amount`.
    value: Optional[Fraction] = None

    def __post_init__(self):
        self.amount = to_fraction(self.amount)
        if self.value is not None:
            self.value = to_fraction(self.value)


@dataclass
class Txn:
    """A single normalised transaction, ready to categorise and write."""

    date: date
    description: str
    legs: List[Leg] = field(default_factory=list)

    # Provenance — used for dedupe and for the review sheet.
    source: str = ""              # "wise-api", "bbva-csv", ...
    source_id: str = ""           # the source's own unique id, where it has one
    reference: str = ""
    counterparty: str = ""

    # Set by the categoriser when it cannot decide on its own.
    needs_review: bool = False
    review_reason: str = ""

    # Set by an adapter that already knows both sides — a conversion between
    # two of your own balances, say — so the categoriser leaves it alone.
    balanced_by_construction: bool = False

    # Set when a conditional fallback classified this rather than a named rule,
    # so the review sheet can say which transactions were covered by a category
    # default rather than an explicit decision about this merchant.
    matched_fallback: str = ""

    @property
    def primary(self) -> Optional[Leg]:
        """The bank-account leg — the one whose account is already known."""
        return self.legs[0] if self.legs else None

    @property
    def currency(self) -> str:
        """Transaction currency: that of the originating bank leg."""
        return self.primary.currency if self.primary else ""

    def signature(self):
        """Key used to recognise this transaction if it is already in the book.

        Deliberately excludes description: banks reword the same transaction
        between an export and a later re-export, but never the date, the
        account or the amount.
        """
        p = self.primary
        return (self.date, p.account, p.amount, p.currency) if p else None

    def is_balanced(self) -> bool:
        """True when every currency present nets to zero across the legs.

        Single-currency transactions must net to zero on their own. Cross-
        currency ones never will — the trading accounts do that job — so this
        only asserts the same-currency case.
        """
        by_ccy = {}
        for leg in self.legs:
            by_ccy.setdefault(leg.currency, Fraction(0))
            by_ccy[leg.currency] += leg.amount
        if len(by_ccy) > 1:
            return True
        return all(v == 0 for v in by_ccy.values())
