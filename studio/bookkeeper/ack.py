"""The acknowledged-not-new list.

A possible duplicate that a human has checked and confirmed is already in the
book would otherwise be listed again on every dry run, because it is still a
same-amount match a day or two off. This file remembers the decision, keyed by
`Txn.ack_key()` (the bank's transaction ID where it has one).

It sits beside the rules file, not in this repo: the keys are bank IDs and
descriptions, which is private data.
"""

import os
from typing import Iterable, Set

import yaml

ACK_FILENAME = "bookkeeper-acknowledged.yaml"


def default_ack_path(rules_path: str) -> str:
    explicit = os.environ.get("BOOKKEEPER_ACK")
    if explicit:
        return explicit
    return os.path.join(os.path.dirname(rules_path or "."), ACK_FILENAME)


def load(path: str) -> Set[str]:
    if not path or not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return {str(k) for k in (data.get("acknowledged") or [])}


def add(path: str, keys: Iterable[str]) -> int:
    """Record keys; returns how many were new."""
    current = load(path)
    fresh = [k for k in keys if k not in current]
    if not fresh:
        return 0
    merged = sorted(current | set(fresh))
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write("# Possible duplicates confirmed as already in the book.\n"
                 "# Written by `--acknowledge-duplicates`; safe to prune.\n")
        yaml.safe_dump({"acknowledged": merged}, fh, allow_unicode=True,
                       default_flow_style=False)
    os.replace(tmp, path)
    return len(fresh)
