#!/usr/bin/env python3
"""Check the Asana template and every registered project against studio conventions.

Read-only. Reports drift and exits non-zero on error-level drift, so it can run from the
ops worktree on a schedule. It never writes to Asana: conforming the template is a separate,
deliberate write, and needs Mark's PAT rather than bainbot's (bainbot's membership on the
template is comment_only). See docs/gods/hermes/asana-conform.md.

Usage:
    python3 studio/scripts/asana_conform.py                # all projects + template
    python3 studio/scripts/asana_conform.py --project TSTY  # one project
    python3 studio/scripts/asana_conform.py --template      # template only
    python3 studio/scripts/asana_conform.py --json          # machine-readable

Conventions checked are those the tooling actually reads — see
$STUDIO_CONTENT_DIR/research/2026-11-06-asana-project-audit.md for why each one is here.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sync  # noqa: E402  (sync.py loads studio/.env and owns the API helpers)

# Sections the tooling depends on, in the order the template should hold them.
# NEXT UP   — sync.py --task-section default, /qa-capture
# STALLED   — /blocked-sweep
# DONE, SOMEDAY/MAYBE — /studio-ghost-projects
EXPECTED_SECTIONS = ["DOING", "NEXT UP", "TO DO", "STALLED", "DONE", "SOMEDAY/MAYBE"]
REQUIRED_SECTIONS = {
    "NEXT UP": "sync.py --create-task and /qa-capture place tasks there",
    "DONE": "/studio-ghost-projects reads it to spot finished projects",
}

# Queues run their own section set by design (ADR 009 / ADR 017).
QUEUE_PREFIXES = {"SL", "SLT", "SLK"}

CANONICAL_PRIORITY_GID = sync.PRIORITY_FIELD_GID
DUPLICATE_PRIORITY_GIDS = {"1206348378137579"}

# Enum options the template ships with. Any project still holding the full set
# verbatim has never had its own scope or feature list authored.
INHERITED_OPTIONS = {
    "Features": {
        "Direct Downloads", "Subscriptions", "Search", "Testimonials", "Homepage",
        "FAQs", "Taxonomies", "CTAs", "Reduce Media Library", "Team Page",
    },
    "Scope": {
        "0: Out of Scope", "1. Redesign Home", "2. Pricing Page", "3. Search",
        "4. Taxonomies", "5. CTAs", "6. Free Membership", "7. FAQs",
        "8. Media Library Size", "9. Team", "10. Testimonials",
    },
}

PROJECT_FIELDS = "custom_field_settings.custom_field.name,custom_field_settings.custom_field.gid"


def required_field_gids() -> dict:
    """Shared fields every synced project must have attached, by name."""
    return {
        "Local ID": sync.SHARED_FIELD_GID,
        "Last Synced": sync.LAST_SYNCED_FIELD_GID,
    }


def paged(path: str, params: dict) -> list:
    """Every page of a collection endpoint. Asana caps a page at 100."""
    out, params = [], dict(params, limit=100)
    while True:
        resp = sync._get(path, params=params)
        out += resp.get("data", [])
        nxt = (resp.get("next_page") or {}).get("offset")
        if not nxt:
            return out
        params = dict(params, offset=nxt)


def fetch(gid: str) -> tuple:
    proj = sync._get(f"/projects/{gid}", params={"opt_fields": f"name,archived,{PROJECT_FIELDS}"})["data"]
    secs = [s["name"] for s in paged(f"/projects/{gid}/sections", {"opt_fields": "name"})]
    return proj, secs


def check_sections(secs: list, prefix: str) -> list:
    out = []
    if prefix in QUEUE_PREFIXES:
        return out
    for name, why in REQUIRED_SECTIONS.items():
        if name not in secs:
            out.append(("error", f"missing section '{name}' — {why}"))
    for name in EXPECTED_SECTIONS:
        if name not in secs and name not in REQUIRED_SECTIONS:
            out.append(("warn", f"no '{name}' section"))
    dupes = {n for n in secs if secs.count(n) > 1}
    for n in sorted(dupes):
        out.append(("warn", f"duplicate section name '{n}'"))
    for n in secs:
        if n.lower().startswith("untitled") or n == "(no section)":
            out.append(("warn", f"stray '{n}'"))
    present = [n for n in EXPECTED_SECTIONS if n in secs]
    actual = [n for n in secs if n in EXPECTED_SECTIONS]
    if present != actual:
        out.append(("warn", f"section order is {' > '.join(actual)}, convention is {' > '.join(present)}"))
    return out


def check_fields(proj: dict) -> list:
    out = []
    attached = {}
    for cfs in proj.get("custom_field_settings", []):
        cf = cfs["custom_field"]
        attached.setdefault(cf["name"], []).append(cf["gid"])

    for name, gid in required_field_gids().items():
        if not gid:
            continue
        if gid not in [g for gs in attached.values() for g in gs]:
            out.append(("error", f"'{name}' ({gid}) not attached — run sync.py --setup"))

    pri = attached.get("Priority", [])
    if pri and CANONICAL_PRIORITY_GID not in pri:
        wrong = ", ".join(pri)
        out.append(("error",
                    f"Priority is field {wrong}, not the canonical {CANONICAL_PRIORITY_GID} — "
                    f"the mirror reads the canonical field and will render 'none'"))
    for name, gids in attached.items():
        if len(gids) > 1:
            out.append(("warn", f"field '{name}' attached twice ({', '.join(gids)})"))
    return out


def check_inherited_options(proj: dict) -> list:
    out = []
    for cfs in proj.get("custom_field_settings", []):
        cf = cfs["custom_field"]
        expected = INHERITED_OPTIONS.get(cf["name"])
        if not expected:
            continue
        full = sync._get(f"/custom_fields/{cf['gid']}",
                         params={"opt_fields": "name,enum_options.name,enum_options.enabled"})["data"]
        enabled = {o["name"] for o in full.get("enum_options") or [] if o.get("enabled")}
        if enabled and enabled == expected:
            out.append(("warn",
                        f"'{cf['name']}' still holds the template's placeholder options verbatim "
                        f"({len(enabled)} of them) — never authored for this project"))
    return out


def check_priority_divergence(gid: str) -> list:
    """Tasks carrying both Priority fields with different values."""
    out = []
    if not DUPLICATE_PRIORITY_GIDS:
        return out
    try:
        tasks = paged(f"/projects/{gid}/tasks", {
            "opt_fields": "name,custom_fields.gid,custom_fields.display_value,completed",
            "completed_since": "now"})
    except Exception as e:
        return [("warn", f"could not read tasks for Priority check: {str(e)[:80]}")]
    dis, orphan = [], 0
    for t in tasks:
        if t.get("completed"):
            continue
        vals = {c["gid"]: c.get("display_value") for c in t.get("custom_fields") or []}
        canon = vals.get(CANONICAL_PRIORITY_GID)
        for dup in DUPLICATE_PRIORITY_GIDS:
            other = vals.get(dup)
            if other and canon and other != canon:
                dis.append(f"{t['name'][:40]} ({canon} vs {other})")
            elif other and not canon:
                orphan += 1
    if orphan:
        out.append(("error", f"{orphan} task(s) have a priority only on the duplicate field — mirror shows 'none'"))
    if dis:
        out.append(("error", f"{len(dis)} task(s) disagree between the two Priority fields: " + "; ".join(dis[:3])))
    return out


def audit(prefix: str, gid: str, is_template: bool) -> dict:
    issues = []
    try:
        proj, secs = fetch(gid)
    except Exception as e:
        return {"prefix": prefix, "gid": gid, "issues": [("error", f"could not read project: {str(e)[:120]}")]}
    issues += check_sections(secs, prefix)
    if is_template:
        # The template does not need Local ID / Last Synced attached — sync.py --setup
        # adds them to the clone. Everything else about its fields still applies.
        issues += [i for i in check_fields(proj) if "not attached" not in i[1]]
    else:
        issues += check_fields(proj)
    issues += check_inherited_options(proj)
    if not is_template:
        issues += check_priority_divergence(gid)
    return {"prefix": prefix, "gid": gid, "name": proj.get("name"),
            "archived": proj.get("archived"), "sections": secs, "issues": issues}


def main() -> int:
    ap = argparse.ArgumentParser(description="Check Asana projects against studio conventions")
    ap.add_argument("--project", metavar="PREFIX", help="check one project by prefix")
    ap.add_argument("--template", action="store_true", help="check the template only")
    ap.add_argument("--json", action="store_true", dest="as_json", help="machine-readable output")
    args = ap.parse_args()

    targets = []
    if args.template or not args.project:
        targets.append(("TEMPLATE", sync.TEMPLATE_PROJECT_GID, True))
    if not args.template:
        for p in sync.discover_projects(filter_prefix=args.project, include_inactive=True, quiet=True):
            if p.gid:
                targets.append((p.prefix, p.gid, False))

    results = [audit(*t) for t in targets]

    if args.as_json:
        print(json.dumps(results, indent=1))
    else:
        errors = warns = 0
        for r in results:
            errs = [i for i in r["issues"] if i[0] == "error"]
            wrs = [i for i in r["issues"] if i[0] == "warn"]
            errors += len(errs)
            warns += len(wrs)
            if not r["issues"]:
                print(f"OK    {r['prefix']}")
                continue
            print(f"\n{r['prefix']}  ({r.get('name') or '?'}{', archived' if r.get('archived') else ''})")
            for level, msg in errs + wrs:
                print(f"  {'ERROR' if level == 'error' else 'warn '}  {msg}")
        print(f"\n{len(results)} project(s) checked — {errors} error(s), {warns} warning(s)")
        return 1 if errors else 0
    return 1 if any(i[0] == "error" for r in results for i in r["issues"]) else 0


if __name__ == "__main__":
    sys.exit(main())
