"""Append a confirmed decision to the rules file.

The rules file is a cache of decisions, not a hand-maintained document: the
skill proposes an account, Mark confirms, and the decision is written here so
the same merchant is never asked about twice.

Text insertion rather than a YAML round-trip, because round-tripping through
PyYAML would strip every comment in the file — and the comments are half of
what makes it reviewable.
"""

import os
import re
from typing import Optional

import yaml


class RuleExists(Exception):
    """Raised when a rule for this merchant is already present."""


def _next_top_level_key(lines, start: int) -> int:
    """Index of the next top-level YAML key after `start`, or end of file."""
    for i in range(start + 1, len(lines)):
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*:", lines[i]):
            return i
    return len(lines)


def append_rule(path: str, match: str, account: str, currency: Optional[str] = None,
                direction: Optional[str] = None, date_from: Optional[str] = None,
                date_to: Optional[str] = None, note: Optional[str] = None,
                account_contains: Optional[str] = None,
                replace: bool = False) -> str:
    """Add a rule to the end of the `rules:` block. Returns the text added.

    With `replace`, an existing rule of the identical scope is rewritten in
    place instead of raising RuleExists. Keys the new call does not carry
    (`regex`, `review`, ...) are dropped, so the old block is reported back in
    the returned text for the operator to check.
    """
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()

    # The same merchant string can legitimately appear twice under different
    # scopes — "mark crawford bain" is a transfer to the personal profile when
    # seen from the business account, and an owner's-draw settlement when seen
    # from the personal one. Only an identical SCOPE is a duplicate.
    scope = (match.lower(), direction, account_contains, currency,
             str(date_from) if date_from else None,
             str(date_to) if date_to else None)
    existing = yaml.safe_load(content) or {}
    clash_index = None
    for idx, rule in enumerate(existing.get("rules") or []):
        if (str(rule.get("match", "")).lower(),
                rule.get("direction"), rule.get("account_contains"),
                rule.get("currency"),
                str(rule["from"]) if rule.get("from") else None,
                str(rule["to"]) if rule.get("to") else None) == scope:
            if not replace:
                raise RuleExists(
                    "A rule for %r with this exact scope already exists, "
                    "pointing at %s. Re-run with --replace to change it."
                    % (match, rule.get("account"))
                )
            clash_index = idx
            break

    lines = content.splitlines(keepends=True)
    rules_at = next(
        (i for i, l in enumerate(lines) if re.match(r"^rules:", l)), None
    )
    if rules_at is None:
        raise SystemExit("No `rules:` block in %s" % path)
    insert_at = _next_top_level_key(lines, rules_at)

    old_text = ""
    if clash_index is not None:
        # The k-th list item in the block is the k-th rule in the parsed YAML.
        starts = [i for i in range(rules_at + 1, insert_at)
                  if re.match(r"^\s*- ", lines[i])]
        start = starts[clash_index]
        end = start + 1
        while end < insert_at and re.match(r"^\s{4,}\S", lines[end]) \
                and not lines[end].lstrip().startswith("#"):
            end += 1
        old_text = "".join(lines[start:end])
        del lines[start:end]
        insert_at = start

    # Step back over trailing blank lines and any comment block introducing the
    # next section, so the new rule joins the list rather than splitting a
    # comment from what it describes. A replacement stays where the old rule was.
    while clash_index is None and insert_at > rules_at + 1 and (
        lines[insert_at - 1].strip() == "" or lines[insert_at - 1].lstrip().startswith("#")
    ):
        insert_at -= 1

    block = []
    if note:
        block.append("  # %s\n" % note)
    block.append('  - match: "%s"\n' % match.replace('"', '\\"'))
    block.append('    account: "%s"\n' % account.replace('"', '\\"'))
    if currency:
        block.append("    currency: %s\n" % currency)
    if direction:
        block.append("    direction: %s\n" % direction)
    if date_from:
        block.append("    from: %s\n" % date_from)
    if date_to:
        block.append("    to: %s\n" % date_to)
    if account_contains:
        block.append('    account_contains: "%s"\n' % account_contains)

    lines[insert_at:insert_at] = block
    new_content = "".join(lines)

    # Never leave the file unparseable.
    parsed = yaml.safe_load(new_content)
    if not any(str(r.get("match", "")).lower() == match.lower()
               for r in (parsed.get("rules") or [])):
        raise SystemExit("Rule did not land in the rules block — file unchanged.")

    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(new_content)
    os.replace(tmp, path)
    added = "".join(block)
    if old_text:
        added += "  (replaced:)\n" + old_text
    return added
