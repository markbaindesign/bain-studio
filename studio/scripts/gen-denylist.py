#!/usr/bin/env python3
"""Emit the client-data denylist, one literal term per line, for grep -F.

This script is versioned; its subject is NOT. Every term is read at run time
from the registry outside the repo, because a committed list of client names
and domains is the exact data the guard exists to keep out of the repo.

Refuses when the registry is absent (a fresh clone, another machine). An empty
denylist would let everything through while appearing to pass.

See ADR 021 and BSTD-875.
"""
import json
import os
import pathlib
import sys

data_home = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
REGISTRY = pathlib.Path(os.environ.get("BAIN_REGISTRY") or f"{data_home}/bain-studio/registry.json")
EXTRA = pathlib.Path(os.environ.get("BAIN_DENYLIST_EXTRA") or f"{data_home}/bain-studio/denylist-extra.txt")

# Never emitted: placeholder values, and the sentinel for an internal client.
SKIP = {"", "none", "Internal", "null", "—", "unknown"}

# Path segments that are containers, not client identifiers.
GENERIC_SEGMENTS = {"www", "clients", "docs", "client docs", "projects", "public_html"}

# The studio's own accounts. They appear in every repo URL and name no client.
OWN_ORGS = {"markbaindesign", "markbain", "bain", "bitbucket.org", "github.com", "ssh.bitbucket.org"}

# A term shorter than this substring-matches ordinary English ("tis" in
# "this"), and anything this short is a project prefix, which is deliberately
# kept in the repo. See ADR 021 addendum, decision 3.
MIN_LEN = 4


def _strip_git(url):
    """str.removesuffix is 3.9+; the system python here is older."""
    return url[:-4] if url.endswith(".git") else url


def terms(entry):
    yield entry.get("client")
    yield entry.get("name")
    yield entry.get("ga4_property")
    yield entry.get("gid")
    yield from entry.get("domains") or []

    # The identifying leaf of a repo URL: git@host:org/<leaf>.git
    repo = (entry.get("repo") or "").strip()
    if repo and not repo.startswith("("):
        leaf = _strip_git(repo.rstrip("/")).split("/")[-1]
        yield leaf
        # A client-owned org is itself an identifier: host[:/]<org>/<leaf>
        parts = _strip_git(repo).replace(":", "/").split("/")
        if len(parts) >= 2 and parts[-2].lower() not in OWN_ORGS:
            yield parts[-2]

    # The working-directory leaf, e.g. .../clients/www/<leaf>
    path = entry.get("path") or ""
    if path:
        yield path.rstrip("/").split("/")[-1]

    # Dropbox client folder names, below the Work/clients container
    cd = entry.get("client_docs") or ""
    segs = cd.strip("/").split("/")
    if "clients" in [s.lower() for s in segs]:
        i = [s.lower() for s in segs].index("clients")
        for seg in segs[i + 1:]:
            if seg.lower() not in GENERIC_SEGMENTS:
                yield seg


def main():
    if not REGISTRY.is_file():
        print(f"gen-denylist: registry not readable at {REGISTRY}", file=sys.stderr)
        print("gen-denylist: refusing to emit an empty denylist — see ADR 021, BSTD-875", file=sys.stderr)
        return 2

    try:
        registry = json.loads(REGISTRY.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        print(f"gen-denylist: cannot parse {REGISTRY}: {exc}", file=sys.stderr)
        return 2

    # Project prefixes stay in the repo by decision: once the prefix-to-client
    # mapping is out of the repo a bare prefix identifies nobody, and the whole
    # toolchain speaks in prefixes. A prefix that reached the denylist would
    # refuse every commit carrying a task ID. See ADR 021 addendum, decision 3.
    prefixes = {
        (e.get("prefix") or "").strip().lower()
        for e in registry.values()
    } - {""}

    out = []
    for entry in registry.values():
        # Client entries only. Internal projects are named freely in a public
        # tooling repo; including them would refuse every commit naming the
        # studio's own work.
        if entry.get("kind") != "client":
            continue
        for term in terms(entry):
            term = (term or "").strip().strip('"')
            if term and term not in SKIP and len(term) >= MIN_LEN \
                    and term.lower() not in OWN_ORGS \
                    and term.lower() not in prefixes:
                out.append(term)

    # Terms with no registry home: client contact names, hosting provider
    # application IDs, the Asana workspace GID, clients with no project file.
    if EXTRA.is_file():
        for line in EXTRA.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line)

    if not out:
        print("gen-denylist: registry held no client entries — refusing", file=sys.stderr)
        return 2

    for term in sorted(set(out), key=str.lower):
        print(term)
    return 0


if __name__ == "__main__":
    sys.exit(main())
