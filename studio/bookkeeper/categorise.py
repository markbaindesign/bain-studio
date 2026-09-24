"""Decide which account the other side of a bank line belongs to.

Source adapters produce a Txn with a single leg: the money that moved in or out
of a known bank account. This module supplies the contra leg.

It is rule-driven rather than clever. A rule matches on the counterparty or the
description and names an account. Anything unmatched is flagged for review and,
by default, held back from the commit rather than guessed at — a wrong expense
account is worse than an absent one, because it silently distorts the IVA
figures the quarterly return is built from.

Rules live outside this repo, in the Accounting config directory, because the
merchant list is personal spending data and this repo is public.
"""

import os
import re
from typing import Dict, List, Optional

import yaml

from .model import Leg, Txn

# This book keeps a per-currency leaf under most expense and income parents —
# "Expenses:Bank Fees:Bank Fees (USD)", not a single "Expenses:Bank Fees". A
# rule therefore names the *family* and the currency picks the leaf. Posting a
# USD expense into a EUR leaf would balance but quietly corrupt every
# per-currency report built on top of it.
def resolve_account(book, template: str, currency: str) -> Optional[str]:
    """Find the real account path for a rule target in a given currency.

    Tries, in order: an explicit {ccy} placeholder; the path as written; the
    path with a currency suffix; and the conventional "Parent:Leaf (CCY)" shape.
    Returns None when nothing in the book fits, so the caller can flag it rather
    than invent an account.
    """
    if "{ccy}" in template:
        candidates = [template.format(ccy=currency)]
    else:
        leaf = template.rsplit(":", 1)[-1]
        candidates = [
            "%s:%s (%s)" % (template, leaf, currency),
            "%s (%s)" % (template, currency),
            template,
        ]

    for path in candidates:
        acc = book.account(path)
        if acc is None:
            continue
        if acc.currency and acc.currency != currency:
            continue
        if acc.type in ("ROOT", "TRADING"):
            continue
        # An account with children is a placeholder. Posting to it balances and
        # raises no error, but the amount then sits outside every per-currency
        # leaf that the reports and the tax figures are built from.
        if acc.has_children:
            continue
        return re.sub(r"^Root Account:", "", acc.path)
    return None


RULES_FILENAME = "bookkeeper-rules.yaml"


def default_rules_path() -> Optional[str]:
    """Locate the rules file the same way the dashboard locates its config.

    FINANCE_CONFIG_DIR is the documented home for user-editable finance
    settings; falling back to a sibling of GNUCASH_DIR keeps this working if
    only the book path is set. No hardcoded home-directory guess — Dropbox is
    not under ~ on every machine here.
    """
    explicit = os.environ.get("BOOKKEEPER_RULES")
    if explicit:
        return explicit
    config_dir = os.environ.get("FINANCE_CONFIG_DIR")
    if config_dir:
        return os.path.join(config_dir, RULES_FILENAME)
    gnucash_dir = os.environ.get("GNUCASH_DIR")
    if gnucash_dir:
        return os.path.join(os.path.dirname(gnucash_dir), "config", RULES_FILENAME)
    return None


CHECK_CURRENCIES = ("EUR", "USD", "GBP")


def check_rules(rules, book):
    """Resolve every rule and fallback target against the book.

    Returns (broken, partial). `broken` are entries whose account resolves in
    none of the currencies they could apply to: they can never post and would
    otherwise surface only at import time, row by row. `partial` resolve for
    some currencies but not others, which is often deliberate (the family
    has no GBP leaf) so it is information, not an error.
    """
    broken, partial = [], []
    entries = [("rule", r.get("match"), r) for r in rules.rules]
    entries += [("fallback", r.get("reason", "default"), r) for r in rules.fallbacks]
    for kind, label, spec in entries:
        template = spec.get("account")
        if not template:
            broken.append((kind, label, "names no account", []))
            continue
        scope = spec.get("currency") or (spec.get("when") or {}).get("currency")
        ccys = (scope,) if scope else CHECK_CURRENCIES
        ok = [c for c in ccys if resolve_account(book, template, c)]
        if not ok:
            broken.append((kind, label, template, list(ccys)))
        elif len(ok) < len(ccys):
            partial.append((kind, label, template, ok))
    return broken, partial


class Rules:
    """Merchant/description to account mapping."""

    def __init__(self, spec: Dict):
        self.spec = spec or {}
        self.rules: List[Dict] = self.spec.get("rules", []) or []
        # Conditional defaults, tried only when no named rule matches. These
        # exist so a single concept ("USD card spending during the trip") is one
        # entry rather than an enumeration of every shop visited once.
        self.fallbacks: List[Dict] = self.spec.get("fallbacks", []) or []
        self.defaults: Dict[str, str] = self.spec.get("defaults", {}) or {}
        self.path = ""

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Rules":
        path = path or default_rules_path()
        if not path or not os.path.exists(path):
            # Silence here would look like "no merchant matched anything";
            # every line would land in review with a misleading reason.
            raise SystemExit(
                "No rules file found%s. Set FINANCE_CONFIG_DIR or "
                "BOOKKEEPER_RULES, or pass --rules." % (" at %s" % path if path else "")
            )
        with open(path, "r", encoding="utf-8") as fh:
            rules = cls(yaml.safe_load(fh) or {})
        rules.path = path
        return rules

    def match(self, txn: Txn) -> Optional[Dict]:
        haystack = " ".join(
            p for p in (txn.counterparty, txn.description, txn.reference) if p
        ).lower()
        for rule in self.rules:
            pattern = str(rule.get("match", "")).lower()
            if not pattern:
                continue
            hit = (
                re.search(pattern, haystack)
                if rule.get("regex")
                else pattern in haystack
            )
            if not hit:
                continue
            # A rule may be scoped to one direction or one source account.
            if "direction" in rule:
                inbound = txn.primary.amount > 0
                if rule["direction"] not in ("in" if inbound else "out"):
                    continue
            if "account_contains" in rule:
                if str(rule["account_contains"]).lower() not in txn.primary.account.lower():
                    continue
            # Date-scoped rules: the same merchant means different things in
            # different periods. US spending during a family trip is money owed
            # back to the business, not the studio's own expense.
            if "from" in rule and str(txn.date) < str(rule["from"]):
                continue
            if "to" in rule and str(txn.date) > str(rule["to"]):
                continue
            if "currency" in rule and txn.primary.currency != rule["currency"]:
                continue
            return rule
        return None

    def fallback(self, txn: Txn) -> Optional[Dict]:
        """Conditional default for a transaction no named rule claimed.

        Scoped by currency, direction and date window rather than by merchant,
        so one entry covers a whole category of one-off spending. A fallback
        marked `confident` is applied as-is; anything else is applied but
        flagged, because a guess that reaches the books unremarked is worse than
        a slow one.
        """
        for spec in self.fallbacks:
            when = spec.get("when", {}) or {}
            leg = txn.primary
            if "currency" in when and leg.currency != when["currency"]:
                continue
            if "direction" in when:
                inbound = leg.amount > 0
                if when["direction"] not in ("in" if inbound else "out"):
                    continue
            if "from" in when and str(txn.date) < str(when["from"]):
                continue
            if "to" in when and str(txn.date) > str(when["to"]):
                continue
            if "account_contains" in when:
                if str(when["account_contains"]).lower() not in leg.account.lower():
                    continue
            if "max_amount" in when and abs(leg.amount) > when["max_amount"]:
                continue
            return spec
        return None


def categorise(txn: Txn, rules: Rules, book) -> Txn:
    """Attach the contra leg to a Txn, or flag it for review.

    Called after any fee leg has been added, and sizes the contra leg to
    whatever the existing legs do not yet account for. For an inbound payment
    of $1,000 that arrived as $993.89 after a $6.11 fee, the legs are
    +993.89 bank and +6.11 charges, so the contra is -1,000 — the gross income,
    which is the figure the books and the IVA return both want.
    """
    if txn.balanced_by_construction:
        return txn  # adapter already produced a complete transaction

    bank = txn.primary
    outstanding = sum(leg.amount for leg in txn.legs)
    rule = rules.match(txn)

    if rule is None:
        rule = rules.fallback(txn)

    if rule is None:
        txn.needs_review = True
        txn.review_reason = "No rule matched %r" % (
            txn.counterparty or txn.description or "(no description)"
        )
        return txn

    template = rule.get("account")
    if not template:
        txn.needs_review = True
        txn.review_reason = "Rule matched %r but names no account" % rule.get("match")
        return txn

    account = resolve_account(book, template, bank.currency)
    if account is None:
        txn.needs_review = True
        txn.review_reason = (
            "Rule matched %r but no %s account exists for %s — create it in "
            "GnuCash first" % (rule.get("match"), template, bank.currency)
        )
        return txn

    txn.legs.append(Leg(account=account, amount=-outstanding, currency=bank.currency))

    if rule.get("review") or ("when" in rule and not rule.get("confident")):
        # Either a merchant that is usually, but not always, one thing — or a
        # fallback that has not been declared settled.
        txn.needs_review = True
        txn.review_reason = rule.get(
            "review_reason",
            "Matched the %r fallback, not a named rule — confirm"
            % rule.get("reason", "default"),
        )
    elif "when" in rule:
        txn.matched_fallback = rule.get("reason", "fallback")
    return txn
