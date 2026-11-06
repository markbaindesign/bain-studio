#!/usr/bin/env python3
"""Shared logic for the client-data commit guard.

Refuses a commit whose ADDED lines, or whose message, carry anything that
identifies a client. The terms come from the registry outside this repo via
studio/scripts/gen-denylist.py — a committed list of client names would be the
very thing this guard exists to keep out.

See CLAUDE.md "No client data. Ever.", ADR 021 and BSTD-875.
"""
import os
import re
import subprocess
import sys

SKIP_ENV = "BAIN_SKIP_CLIENT_GUARD"

# CHANGELOG.md is the one deliberate exception: past release entries stay as
# written, since the identical text is in git log either way. New entries should
# still use prefixes - that is a rule, not something this guard enforces.
EXCLUDE_PATHS = {"CHANGELOG.md"}


def repo_root():
    return subprocess.run(["git", "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True, check=True).stdout.strip()


def denylist(root):
    """Terms, or None when the registry cannot answer.

    None means REFUSE, never 'nothing matched'. An unconfigured machine is
    exactly where client data would slip through unnoticed.
    """
    script = os.path.join(root, "studio", "scripts", "gen-denylist.py")
    if not os.path.isfile(script):
        return None
    try:
        p = subprocess.run([sys.executable, script], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        return None
    terms = [t for t in (line.strip() for line in p.stdout.splitlines()) if t]
    return terms or None


def compile_terms(terms):
    # Word boundaries, so a short term cannot match inside an ordinary word.
    # \b is wrong next to a non-word char, so only pad where the edge is a word
    # char - that keeps domains and hyphenated slugs matching.
    out = []
    for t in terms:
        esc = re.escape(t)
        left = r"\b" if t[:1].isalnum() else ""
        right = r"\b" if t[-1:].isalnum() else ""
        out.append((t, re.compile(left + esc + right, re.I)))
    return out


def no_registry_message():
    return (
        "client-guard: cannot build the client-data denylist.\n"
        "  The registry is missing, unreadable, or holds no client entries:\n"
        "    $XDG_DATA_HOME/bain-studio/registry.json\n"
        "\n"
        "  This commit was NOT checked, so it is refused rather than let through.\n"
        "\n"
        "  Fix: run studio/scripts/setup-machine.sh, or copy the registry to this\n"
        "  machine. For a deliberate one-off:\n"
        f"    {SKIP_ENV}=1 git commit ...\n"
        "\n"
        "  See CLAUDE.md \"No client data. Ever.\" and ADR 021.\n"
    )


def report(hits, what):
    print(f"client-guard: {what} carries client data.\n", file=sys.stderr)
    for where, term, text in hits[:20]:
        print(f"  {where}: {term!r}", file=sys.stderr)
        print(f"    {text.strip()[:120]}", file=sys.stderr)
    if len(hits) > 20:
        print(f"  ... and {len(hits) - 20} more", file=sys.stderr)
    print(
        "\n  Client identity does not go in this repo - it is public. Put it in the\n"
        "  registry or Dropbox and refer to the project by its PREFIX instead.\n"
        "  Prefixes are fine; names, domains, hosts and IDs are not.\n"
        f"\n  Deliberate one-off: {SKIP_ENV}=1 git commit ...\n",
        file=sys.stderr)


def skipped():
    if os.environ.get(SKIP_ENV):
        print(f"client-guard: skipped ({SKIP_ENV} set)", file=sys.stderr)
        return True
    return False
