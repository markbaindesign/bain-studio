#!/usr/bin/env python3
"""Mark the critical path of an Asana project in a "Critical Path" field.

Asana's own critical-path highlight is not available on every plan, so this
works it out from the project's own dates and dependencies and writes the
answer to a single-select field. Colour the Gantt or Timeline by that field and
the path shows up.

The calculation is a backward pass over the schedule as it stands:

- The target is the open milestone with the latest due date.
- Only open, dated tasks and milestones that lead to the target count.
- Each item occupies its working days from start to due (one day when there is
  no start date; a milestone occupies its own day). A blocker must finish the
  working day before the item it blocks starts, the rule Asana's
  finish-to-start dependencies apply.
- An item's latest finish is the latest day it could end without moving the
  target. Its slack is the working days between its due date and that.
- The critical path is the driving path: from the target, back through the
  blocker with the least slack at each step, plus anything with no slack at
  all. A plan with buffer between milestones has almost no zero-slack work,
  so this marks the chain that runs out of room first.

Working days are Monday to Friday. Holidays are not modelled.

Usage:
    python3 studio/critical_path.py --project PSK            # write the field
    python3 studio/critical_path.py --project PSK --dry-run  # print, write nothing
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

FIELD_NAME = "Critical Path"
OPTION_NAME = "Critical"


# --- working days ------------------------------------------------------------

def is_workday(d: date) -> bool:
    return d.weekday() < 5


def wd_add(d: date, n: int) -> date:
    """Move n working days from d (n may be negative; 0 returns d)."""
    step = 1 if n >= 0 else -1
    left = abs(n)
    while left:
        d += timedelta(days=step)
        if is_workday(d):
            left -= 1
    return d


def wd_diff(a: date, b: date) -> int:
    """Working days from a to b: positive when b is later, 0 when the same day."""
    if a == b:
        return 0
    sign = 1 if b > a else -1
    lo, hi = (a, b) if b > a else (b, a)
    n, d = 0, lo
    while d < hi:
        d += timedelta(days=1)
        if is_workday(d):
            n += 1
    return sign * n


def wd_count(start: date, due: date) -> int:
    """Working days occupied from start to due inclusive, at least 1."""
    return max(1, wd_diff(start, due) + (1 if is_workday(start) else 0))


# --- the calculation ---------------------------------------------------------

@dataclass
class Item:
    gid: str
    name: str
    due: date
    start: date | None = None
    milestone: bool = False
    blockers: list = field(default_factory=list)  # gids of items that block this one

    @property
    def duration(self) -> int:
        if self.milestone or not self.start:
            return 1
        return wd_count(self.start, self.due)


def find_cycle(items: dict):
    """A list of gids forming a dependency cycle, or None."""
    state = {}

    def visit(g, path):
        state[g] = 1
        for b in items[g].blockers:
            if b not in items:
                continue
            if state.get(b) == 1:
                return path[path.index(b):] + [b] if b in path else [b, g]
            if b not in state:
                found = visit(b, path + [b])
                if found:
                    return found
        state[g] = 2
        return None

    for g in items:
        if g not in state:
            found = visit(g, [g])
            if found:
                return found
    return None


def critical_items(items: dict) -> tuple[set, dict, str | None]:
    """(critical gids, slack by gid, target gid) for a dict of gid -> Item.

    Items must already be open and dated. Blockers outside the dict are ignored.
    Raises ValueError on a dependency cycle, which has no critical path.
    """
    cycle = find_cycle(items)
    if cycle:
        raise ValueError("dependency cycle: " + " -> ".join(items[g].name for g in cycle))
    milestones = [i for i in items.values() if i.milestone]
    if not milestones:
        return set(), {}, None
    target = max(milestones, key=lambda i: (i.due, i.name)).gid

    succ = {g: [] for g in items}
    for it in items.values():
        for b in it.blockers:
            if b in items:
                succ[b].append(it.gid)

    # Items that lead to the target: walk blockers back from it.
    reach, stack = {target}, [target]
    while stack:
        for b in items[stack.pop()].blockers:
            if b in items and b not in reach:
                reach.add(b)
                stack.append(b)

    latest_finish: dict = {}

    def lf(g):
        if g in latest_finish:
            return latest_finish[g]
        if g == target:
            latest_finish[g] = items[g].due
            return latest_finish[g]
        best = None
        for s in succ[g]:
            if s not in reach:
                continue
            s_lf = lf(s)
            s_latest_start = wd_add(s_lf, -(items[s].duration - 1))
            cand = wd_add(s_latest_start, -1)
            best = cand if best is None or cand < best else best
        latest_finish[g] = best if best is not None else items[g].due
        return latest_finish[g]

    slack = {g: wd_diff(items[g].due, lf(g)) for g in reach}

    # The driving path: from the target, follow the blocker(s) with the least
    # slack. A plan with buffer between milestones has little or no zero-slack
    # work, so "slack <= 0" alone marks almost nothing; the driving path is the
    # chain that runs out of room first, and it includes any zero-slack items.
    path, stack = {target}, [target]
    while stack:
        g = stack.pop()
        blockers = [b for b in items[g].blockers if b in reach]
        if not blockers:
            continue
        least = min(slack[b] for b in blockers)
        for b in blockers:
            if slack[b] == least and b not in path:
                path.add(b)
                stack.append(b)
    path |= {g for g, s in slack.items() if s <= 0}
    return path, slack, target


# --- Asana -------------------------------------------------------------------

def _sync():
    sys.path.insert(0, str(Path(__file__).parent))
    import sync  # noqa: E402  (loads studio/.env, gives the bainbot HTTP helpers)
    return sync


def fetch_items(sync, project_gid: str):
    """(open dated Items by gid, field value by gid for every open task)."""
    params = {
        "project": project_gid, "limit": 100,
        "opt_fields": "name,start_on,due_on,completed,resource_subtype,"
                      "dependencies.gid,custom_fields.gid,custom_fields.enum_value.gid",
    }
    rows, offset = [], None
    while True:
        if offset:
            params["offset"] = offset
        page = sync._get("/tasks", params)
        rows += page["data"]
        offset = (page.get("next_page") or {}).get("offset")
        if not offset:
            break

    items, rows_by_gid = {}, {}
    for t in rows:
        if t.get("completed"):
            continue
        rows_by_gid[t["gid"]] = t
        if not t.get("due_on"):
            continue
        items[t["gid"]] = Item(
            gid=t["gid"], name=t["name"],
            due=date.fromisoformat(t["due_on"]),
            start=date.fromisoformat(t["start_on"]) if t.get("start_on") else None,
            milestone=t.get("resource_subtype") == "milestone",
            blockers=[d["gid"] for d in t.get("dependencies") or []],
        )
    return items, rows_by_gid


def ensure_field(sync, project_gid: str, dry_run: bool):
    """(field gid, option gid) for the shared Critical Path field, attached to the project."""
    fgid = os.getenv("ASANA_CRITICAL_PATH_FIELD_GID")
    if not fgid:
        params, offset = {"limit": 100, "opt_fields": "name"}, None
        while True:
            if offset:
                params["offset"] = offset
            page = sync._get(f"/workspaces/{sync.WORKSPACE_GID}/custom_fields", params)
            hit = next((f for f in page["data"] if f["name"] == FIELD_NAME), None)
            if hit:
                fgid = hit["gid"]
                break
            offset = (page.get("next_page") or {}).get("offset")
            if not offset:
                break
    if not fgid:
        if dry_run:
            return None, None
        fgid = sync._post("/custom_fields", {"data": {
            "workspace": sync.WORKSPACE_GID, "name": FIELD_NAME,
            "resource_subtype": "enum",
            "enum_options": [{"name": OPTION_NAME, "color": "red"}],
        }})["data"]["gid"]
        print(f"Created '{FIELD_NAME}' field {fgid}; add ASANA_CRITICAL_PATH_FIELD_GID={fgid} to studio/.env")

    f = sync._get(f"/custom_fields/{fgid}", {"opt_fields": "enum_options.name,enum_options.enabled"})["data"]
    opt = next((o["gid"] for o in f["enum_options"] if o["name"] == OPTION_NAME and o["enabled"]), None)

    settings = sync._get(f"/projects/{project_gid}/custom_field_settings",
                         {"opt_fields": "custom_field.gid", "limit": 100})["data"]
    if fgid not in {s["custom_field"]["gid"] for s in settings} and not dry_run:
        sync._post(f"/projects/{project_gid}/addCustomFieldSetting", {"data": {"custom_field": fgid}})
    return fgid, opt


def current_value(row: dict, fgid: str):
    for cf in row.get("custom_fields") or []:
        if cf["gid"] == fgid:
            return (cf.get("enum_value") or {}).get("gid")
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--project", required=True, metavar="PREFIX")
    ap.add_argument("--dry-run", action="store_true", help="print the path, write nothing")
    args = ap.parse_args(argv)

    sys.path.insert(0, str(Path(__file__).parent))
    import registry
    entry = registry.resolve(args.project)
    if not entry or not entry.get("gid"):
        sys.exit(f"Unknown project or no Asana GID: {args.project}")
    project_gid = entry["gid"]

    sync = _sync()
    items, rows = fetch_items(sync, project_gid)
    try:
        crit, slack, target = critical_items(items)
    except ValueError as e:
        sys.exit(f"{args.project}: {e}")
    if not target:
        sys.exit(f"{args.project}: no open dated milestone, so no path to compute")

    print(f"{args.project}: target '{items[target].name}' ({items[target].due}); "
          f"{len(crit)} critical of {len(slack)} on a chain to it")
    for g in sorted(crit, key=lambda g: (items[g].due, items[g].name)):
        kind = "M" if items[g].milestone else "T"
        note = (f"conflict: {-slack[g]} working day(s) late" if slack[g] < 0
                else f"slack {slack[g]}")
        print(f"  {items[g].due}  {kind}  {note:>12}  {items[g].name}")

    fgid, opt = ensure_field(sync, project_gid, args.dry_run)
    if args.dry_run:
        return
    if not opt:
        sys.exit(f"'{FIELD_NAME}' field has no enabled '{OPTION_NAME}' option")
    changed = 0
    for g, row in rows.items():
        want = opt if g in crit else None
        if current_value(row, fgid) != want:
            sync._put(f"/tasks/{g}", {"data": {"custom_fields": {fgid: want}}})
            changed += 1
    print(f"Updated {changed} task(s)")


if __name__ == "__main__":
    main()
