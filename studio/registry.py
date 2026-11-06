#!/usr/bin/env python3
"""Resolve studio project identity from one place.

Project identity lived in four disagreeing sources (ADR 021). It now lives in
a registry outside this repo, because this repo is public and the registry
names clients:

    $XDG_DATA_HOME/bain-studio/registry.json

This module is the only thing that knows where that is. Everything else asks it
for a prefix, a path or the project list.

**It falls back to `docs/projects/*.md` and `projects.json` when the registry is
absent**, and says which source it used. The fallback exists for one reason: the
ops worktree runs scheduled jobs off a release tag, so code reaching the new
path must keep working on a machine where the registry has not been written yet.
The fallback is removed once ops is proven on the registry — see BSTD-875.

CLI:
    python3 studio/registry.py --list
    python3 studio/registry.py --prefix KF-WEB --field path
    python3 studio/registry.py --json
    python3 studio/registry.py --source

Overrides, all for testing or for a machine laid out differently:
    BAIN_REGISTRY        the registry file
    BAIN_PROJECTS_JSON   the fallback's projects.json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent

SOURCE_REGISTRY = "registry"
SOURCE_FALLBACK = "fallback"


def registry_path() -> Path:
    if os.environ.get("BAIN_REGISTRY"):
        return Path(os.environ["BAIN_REGISTRY"]).expanduser()
    data_home = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    return Path(data_home) / "bain-studio" / "registry.json"


def _frontmatter(text: str) -> dict:
    """Parse a leading --- block. Deliberately not yaml: one dependency fewer,
    and the frontmatter here is flat key: value only."""
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        km = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", line)
        if km:
            out[km.group(1)] = km.group(2).strip().strip('"').strip("'")
    return out


def _load_from_registry():
    p = registry_path()
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"registry: {p} unreadable ({exc}); falling back", file=sys.stderr)
        return None
    if not isinstance(data, dict) or not data:
        return None
    return data


def _load_from_fallback(repo_root=None):
    """docs/projects/*.md frontmatter, plus projects.json for entries that have
    no project file of their own. Two projects were only ever in projects.json.

    `repo_root` lets a caller scope the scan to its own idea of the repo rather
    than this file's location, so a caller under test is not silently answered
    from the real tree.
    """
    out = {}
    root = Path(repo_root) if repo_root else REPO_ROOT
    docs = root / "docs" / "projects"
    if docs.is_dir():
        for f in sorted(docs.glob("*.md")):
            fm = _frontmatter(f.read_text(errors="replace"))
            if not fm.get("prefix"):
                continue
            out[f.stem] = {
                "kind": "client" if fm.get("type") == "client" else "internal",
                "prefix": fm.get("prefix", ""),
                "name": fm.get("name", ""),
                "client": fm.get("client", ""),
                "status": fm.get("status", "active"),
                "path": fm.get("path", ""),
                "repo": fm.get("repo", ""),
                "gid": fm.get("asana_project_gid") or fm.get("asana_gid") or "",
                "ga4_property": fm.get("ga4_property", ""),
                "domains": [],
            }
    # projects.json is gitignored, so it is absent from a feature worktree and
    # symlinked into the ops one. The override makes that branch testable.
    pj = Path(os.environ["BAIN_PROJECTS_JSON"]).expanduser() \
        if os.environ.get("BAIN_PROJECTS_JSON") else root / "studio" / "projects.json"
    if pj.is_file():
        try:
            entries = json.loads(pj.read_text())
        except (OSError, json.JSONDecodeError):
            entries = []
        if isinstance(entries, list):
            known = {(e.get("prefix") or "").upper() for e in out.values()}
            for e in entries:
                pre = (e.get("prefix") or "").upper()
                if not pre or pre in known:
                    continue
                slug = (e.get("path") or pre).rstrip("/").split("/")[-1].lower()
                out[slug] = {
                    "kind": "internal",
                    "prefix": e.get("prefix", ""),
                    "name": e.get("name", ""),
                    "client": "",
                    "status": e.get("status", "active"),
                    "path": e.get("path", ""),
                    "repo": "",
                    "gid": e.get("gid", ""),
                    "ga4_property": "",
                    "domains": [],
                }
    return out or None


def load(prefer_fallback=False, repo_root=None):
    """Return (entries, source). Registry first unless prefer_fallback."""
    if not prefer_fallback:
        data = _load_from_registry()
        if data:
            return data, SOURCE_REGISTRY
    data = _load_from_fallback(repo_root)
    if data:
        return data, SOURCE_FALLBACK
    return {}, SOURCE_FALLBACK


def resolve(prefix, entries=None, repo_root=None, stem=True):
    """Entry for a prefix, case-insensitively. None when unknown.

    With `stem`, a prefix that matches nothing exactly also tries the
    stem form, so "KF" finds "KF-WEB". `/open` has always behaved this way and
    it is kept deliberately. An ambiguous stem — two projects under one stem —
    returns None rather than guessing which was meant.
    """
    if entries is None:
        entries, _ = load(repo_root=repo_root)
    want = (prefix or "").strip().upper()
    if not want:
        return None
    for entry in entries.values():
        if (entry.get("prefix") or "").upper() == want:
            return entry
    if stem:
        hits = [e for e in entries.values()
                if (e.get("prefix") or "").upper().startswith(want + "-")]
        if len(hits) == 1:
            return hits[0]
    return None


def path_for(prefix, entries=None, repo_root=None, stem=True):
    entry = resolve(prefix, entries, repo_root=repo_root, stem=stem)
    if not entry or not entry.get("path"):
        return None
    return Path(entry["path"]).expanduser()


def by_path(path, entries=None, repo_root=None):
    """Entry whose `path` is this directory. None when unknown.

    sync.py discovers projects by walking paths, so it needs the reverse lookup:
    given a project root, what does the registry know about it?
    """
    if entries is None:
        entries, _ = load(repo_root=repo_root)
    try:
        want = Path(path).expanduser().resolve()
    except (OSError, RuntimeError):
        return None
    for entry in entries.values():
        raw = entry.get("path")
        if not raw:
            continue
        try:
            if Path(raw).expanduser().resolve() == want:
                return entry
        except (OSError, RuntimeError):
            continue
    return None


def active(entries=None):
    if entries is None:
        entries, _ = load()
    return {k: v for k, v in entries.items()
            if v.get("status") not in ("paused", "archived")}


def main():
    ap = argparse.ArgumentParser(description="Resolve studio project identity.")
    ap.add_argument("--prefix", help="project prefix to resolve")
    ap.add_argument("--field", help="single field to print (path, gid, name, status, client)")
    ap.add_argument("--list", action="store_true", help="prefix, status and path per project")
    ap.add_argument("--json", action="store_true", help="the whole registry as JSON")
    ap.add_argument("--source", action="store_true", help="print which source was used")
    ap.add_argument("--active", action="store_true", help="omit paused and archived")
    ap.add_argument("--exact", action="store_true",
                    help="do not fall back to stem matching (KF -> KF-WEB)")
    args = ap.parse_args()

    entries, source = load()
    if args.active:
        entries = active(entries)

    if args.source:
        print(f"{source}: {registry_path() if source == SOURCE_REGISTRY else 'docs/projects + projects.json'}")
        return 0
    if not entries:
        print("registry: no projects found in the registry or the fallback", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(entries, indent=2, ensure_ascii=False))
        return 0
    if args.prefix:
        entry = resolve(args.prefix, entries, stem=not args.exact)
        if not entry:
            print(f"registry: unknown prefix {args.prefix!r}", file=sys.stderr)
            return 1
        if args.field:
            value = entry.get(args.field)
            if value in (None, ""):
                print(f"registry: {args.prefix} has no {args.field!r}", file=sys.stderr)
                return 1
            print(value)
        else:
            print(json.dumps(entry, indent=2, ensure_ascii=False))
        return 0
    if args.list:
        for slug, e in sorted(entries.items()):
            print(f"{e.get('prefix',''):<8} {e.get('status',''):<9} {e.get('path','')}")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
