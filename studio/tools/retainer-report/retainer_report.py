#!/usr/bin/env python3
"""Monthly maintenance retainer report.

Computes a retainer client's hour bank for a billing cycle from Harvest time
entries and renders the client-facing report.

    python3 retainer_report.py TSTY
    python3 retainer_report.py TSTY --cycle 2026-10-03
    python3 retainer_report.py EBIZG --json

A cycle runs from the client's cycle_day to the day before the next one,
inclusive: Techstyle's October cycle is 3 Oct to 2 Nov. With no --cycle, the
tool reports the most recent cycle that has finished, which is what the task
on the invoice date is asking for.

Every logged minute draws down the bank, calls, email and meetings included.
Only the task types in clients.yaml excluded_tasks are left out. Hours logged
before the client's first cycle are reported separately, never silently
absorbed.

Output is the report text. It does not touch Gmail or Asana: the draft goes
through the copywriter and then Gmail by hand, so nothing reaches a client
without review.
"""

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import requests
import yaml

HERE = Path(__file__).resolve().parent
ENV = HERE.parents[1] / "studio" / ".env"
if not ENV.exists():
    ENV = HERE.parents[1] / ".env"
BASE = "https://api.harvestapp.com/api/v2"


def load_env():
    """Harvest credentials from studio/.env, without clobbering the real env."""
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v.strip().strip("\"'"))
    token = os.environ.get("HARVEST_TOKEN")
    account = os.environ.get("HARVEST_ACCOUNT_ID")
    if not token or not account:
        sys.exit(f"HARVEST_TOKEN and HARVEST_ACCOUNT_ID must be set (looked in {ENV})")
    return {
        "Authorization": f"Bearer {token}",
        "Harvest-Account-Id": str(account),
        "User-Agent": "BainDesign-RetainerReport/1.0",
    }


def add_months(d, n):
    """Shift a date by n months, clamping the day to the target month's length."""
    total = (d.year * 12 + d.month - 1) + n
    year, month = divmod(total, 12)
    month += 1
    day = d.day
    while True:
        try:
            return date(year, month, day)
        except ValueError:
            day -= 1


def cycle_start_on_or_before(ref, cycle_day):
    """The start of the cycle containing ref."""
    anchor = add_months(date(ref.year, ref.month, 1), 0)
    day = min(cycle_day, (add_months(anchor, 1) - timedelta(days=1)).day)
    this_month = date(ref.year, ref.month, day)
    return this_month if ref >= this_month else add_months(this_month, -1)


def resolve_cycle(cfg, cycle_arg, today):
    """(start, end) for the requested cycle, or the latest finished one."""
    first = cfg["first_cycle"]
    if isinstance(first, str):
        first = date.fromisoformat(first)
    if cycle_arg:
        start = date.fromisoformat(cycle_arg)
    else:
        start = cycle_start_on_or_before(today, cfg["cycle_day"])
        # The cycle containing today has not finished, so step back one.
        if add_months(start, 1) - timedelta(days=1) > today:
            start = add_months(start, -1)
    end = add_months(start, 1) - timedelta(days=1)
    if start < first:
        sys.exit(
            f"Cycle starting {start} is before this client's first cycle ({first}). "
            f"The first report is due {add_months(first, 1)}."
        )
    return start, end, first


def cycles_elapsed(first, start):
    """How many top-ups have landed, counting the one that opens this cycle."""
    n = 0
    cur = first
    while cur <= start:
        n += 1
        cur = add_months(cur, 1)
    return n


def fetch_entries(headers, project_id, frm, to):
    out, page = [], 1
    while True:
        r = requests.get(
            f"{BASE}/time_entries",
            headers=headers,
            params={
                "project_id": project_id,
                "from": frm.isoformat(),
                "to": to.isoformat(),
                "per_page": 100,
                "page": page,
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        out.extend(data["time_entries"])
        if not data.get("next_page"):
            return out
        page = data["next_page"]


def build(cfg, excluded, headers, cycle_arg, today):
    start, end, first = resolve_cycle(cfg, cycle_arg, today)
    # Reach back beyond the first cycle: hours logged before the retainer
    # started are reported, not silently dropped out of the query window.
    entries = fetch_entries(headers, cfg["harvest_project"],
                            first - timedelta(days=400), end)

    counted, excluded_rows, pre_start = [], [], []
    for e in entries:
        task = (e.get("task") or {}).get("name", "")
        row = {
            "date": e["spent_date"],
            "hours": round(e["hours"], 2),
            "task": task,
            "notes": (e.get("notes") or "").strip(),
        }
        spent = date.fromisoformat(e["spent_date"])
        if task in excluded:
            excluded_rows.append(row)
        elif spent < first:
            pre_start.append(row)
        elif start <= spent <= end:
            counted.append(row)
        elif spent < start:
            row["_before_cycle"] = True
            counted.append(row)

    in_cycle = [r for r in counted if not r.get("_before_cycle")]
    used_before = sum(r["hours"] for r in counted if r.get("_before_cycle"))
    used = sum(r["hours"] for r in in_cycle)

    topups = cycles_elapsed(first, start)
    opening = round(topups * cfg["hours_month"] - used_before, 2)
    closing = round(opening - used, 2)

    in_cycle.sort(key=lambda r: r["date"])
    return {
        "prefix": cfg["_prefix"],
        "client": cfg["client_name"],
        "cycle_start": start.isoformat(),
        "cycle_end": end.isoformat(),
        "hours_month": cfg["hours_month"],
        "topups_to_date": topups,
        "opening": opening,
        "used": round(used, 2),
        "closing": closing,
        "next_topup": cfg["hours_month"],
        "next_opening": round(closing + cfg["hours_month"], 2),
        "next_cycle_start": add_months(start, 1).isoformat(),
        "work": in_cycle,
        "excluded": excluded_rows,
        "before_first_cycle": pre_start,
        "thin_notes": [r for r in in_cycle if is_thin(r["notes"])],
        "overdrawn": closing < 0,
    }


VAGUE = {
    "update", "updates", "misc", "miscellaneous", "work", "fixes", "fix",
    "admin", "general", "maintenance", "stuff", "various", "changes", "tweaks",
}


def is_thin(note):
    """A note is thin when it would tell the client nothing on its own."""
    n = note.strip().rstrip(".").lower()
    if not n:
        return True
    words = n.split()
    return len(words) < 2 or n in VAGUE


def fmt_hours(h):
    return f"{h:.2f} h"


def fmt_date(iso):
    d = date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%B')}"


def render(rep, cfg):
    start, end = fmt_date(rep["cycle_start"]), fmt_date(rep["cycle_end"])
    L = []
    L.append(f"Subject: {rep['client']} retainer report: {start} to {end}")
    L.append("")
    L.append(f"Hi {cfg['greeting']}")
    L.append("")
    L.append(f"Here is the retainer summary for {start} to {end}.")
    L.append("")
    if rep["work"]:
        L.append("Work completed")
        for r in rep["work"]:
            note = r["notes"] or f"({r['task']})"
            L.append(f"- {note}: {fmt_hours(r['hours'])}")
    else:
        L.append("Work completed")
        L.append("- No work was logged this cycle.")
    L.append("")
    L.append("Hours")
    L.append(f"- Opening balance: {fmt_hours(rep['opening'])}")
    L.append(f"- Used this cycle: {fmt_hours(rep['used'])}")
    L.append(f"- Closing balance: {fmt_hours(rep['closing'])}")
    L.append("")
    L.append(
        f"{fmt_hours(rep['next_topup'])} is added on {fmt_date(rep['next_cycle_start'])}, "
        f"taking you to {fmt_hours(rep['next_opening'])}. "
        "Banked hours roll over with no cap and no expiry."
    )
    L.append("")
    L.append("All the best")
    L.append("Mark")
    return "\n".join(L)


def render_flags(rep):
    F = []
    if rep["overdrawn"]:
        F.append(
            f"OVERDRAWN: closing balance is {fmt_hours(rep['closing'])}. "
            "Decide whether to bill the overage or absorb it before sending."
        )
    for r in rep["before_first_cycle"]:
        F.append(
            f"BEFORE FIRST CYCLE: {r['date']} {fmt_hours(r['hours'])} "
            f"{r['notes'] or r['task']!r} predates the first paid cycle and is not "
            "drawn from the bank. Confirm it should be free."
        )
    for r in rep["thin_notes"]:
        F.append(
            f"THIN NOTE: {r['date']} {fmt_hours(r['hours'])} note is {r['notes']!r}. "
            "Rewrite it before this goes to the client."
        )
    for r in rep["excluded"]:
        F.append(
            f"NOT CHARGED: {r['date']} {fmt_hours(r['hours'])} on {r['task']!r} "
            f"({r['notes'] or 'no note'}) is excluded from the bank."
        )
    return F


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prefix", help="client prefix from clients.yaml, e.g. TSTY")
    ap.add_argument("--cycle", help="cycle start date YYYY-MM-DD (default: last finished cycle)")
    ap.add_argument("--json", action="store_true", help="emit the computed figures as JSON")
    ap.add_argument("--today", help="override today's date, for testing")
    args = ap.parse_args()

    conf = yaml.safe_load((HERE / "clients.yaml").read_text())
    excluded = set(conf.pop("excluded_tasks", []) or [])
    key = args.prefix.upper()
    if key not in conf:
        sys.exit(f"Unknown client {key!r}. Known: {', '.join(sorted(conf))}")
    cfg = conf[key]
    cfg["_prefix"] = key

    today = date.fromisoformat(args.today) if args.today else date.today()
    rep = build(cfg, excluded, load_env(), args.cycle, today)

    if args.json:
        print(json.dumps(rep, indent=2))
        return

    print(render(rep, cfg))
    flags = render_flags(rep)
    if flags:
        print("\n" + "=" * 62)
        print("REVIEW BEFORE SENDING")
        print("=" * 62)
        for f in flags:
            print(f"- {f}")
    print("\n" + "-" * 62)
    print(f"To: {', '.join(cfg['to'])}")
    if cfg.get("cc"):
        print(f"Cc: {', '.join(cfg['cc'])}")
    print(f"Harvest project {cfg['harvest_project']} | top-ups to date: "
          f"{rep['topups_to_date']} x {fmt_hours(cfg['hours_month'])}")


if __name__ == "__main__":
    main()
