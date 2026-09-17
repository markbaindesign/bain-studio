#!/usr/bin/env python3
"""
Rename a project's task ID prefix, keeping every task's number (PIPE-063 → UAP-063).

Why a script: changing ASANA_TASK_PREFIX in a project's CLAUDE.md on its own makes the next
sync treat every existing OLD-NNN as a foreign ID and re-home it with a fresh sequence number,
scrambling all the IDs. The Local ID values in Asana and in every asana-ids.json have to be
rewritten in the same window, with no sync running in between.

Steps (dry run unless --apply):
  1. Refuse if a sync.py process is running.
  2. Asana: rewrite the Local ID field on every task in the project (all of them, including
     long-completed ones) that holds OLD-NNN.
  3. Every registered project's asana-ids.json: OLD-NNN → NEW-NNN (SL holds foreign IDs too).
  4. Every registered project's asana-mirror.md: task headings and Local ID lines only. Other text
     (notes, progress) is left alone so the next sync doesn't see edits to push.
  5. The project's CLAUDE.md: ASANA_TASK_PREFIX.

References to the old prefix in docs, code and commit history are not touched — update those by hand.

Usage:
    python3 studio/scripts/rename_prefix.py PIPE UAP            # dry run
    python3 studio/scripts/rename_prefix.py PIPE UAP --apply
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sync  # noqa: E402

PREFIX_RE = re.compile(r"^[A-Z][A-Z0-9-]*$")


def sync_running() -> bool:
    r = subprocess.run(["pgrep", "-f", r"studio/sync\.py"], capture_output=True, text=True)
    return bool(r.stdout.strip())


def rename_id(value: str, old: str, new: str) -> str:
    m = re.fullmatch(rf"{re.escape(old)}-(\d+)", value or "")
    return f"{new}-{m.group(1)}" if m else value


def fetch_all_tasks(project_gid: str, field_gid: str) -> list:
    """Every task in the project, completed or not, paging to the end."""
    tasks, offset = [], None
    while True:
        params = {"opt_fields": "name,custom_fields.gid,custom_fields.text_value", "limit": 100}
        if offset:
            params["offset"] = offset
        page = sync._get(f"/projects/{project_gid}/tasks", params)
        for t in page.get("data") or []:
            t["_local_id"] = next((cf.get("text_value") for cf in t.get("custom_fields") or []
                                   if cf.get("gid") == field_gid), None)
            tasks.append(t)
        offset = (page.get("next_page") or {}).get("offset")
        if not offset:
            return tasks


def rewrite_ids_file(path: Path, old: str, new: str) -> tuple:
    data = json.loads(path.read_text())
    tasks = data.get("tasks") or {}
    changed = 0
    for gid, lid in tasks.items():
        renamed = rename_id(lid, old, new)
        if renamed != lid:
            tasks[gid] = renamed
            changed += 1
    return changed, data


def rewrite_mirror(text: str, old: str, new: str) -> tuple:
    pattern = re.compile(rf"^(### |- \*\*Local ID:\*\* ){re.escape(old)}-(\d+)\b", re.M)
    return pattern.subn(rf"\g<1>{new}-\g<2>", text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--apply", action="store_true", help="Make the changes (default is a dry run)")
    args = ap.parse_args()
    old, new = args.old.upper(), args.new.upper()
    if not PREFIX_RE.match(new):
        sys.exit(f"Invalid prefix '{new}'")

    projects = sync.discover_projects(filter_prefix=old)
    if not projects:
        sys.exit(f"No registered project with prefix {old}")
    if sync.discover_projects(filter_prefix=new):
        sys.exit(f"Prefix {new} is already in use")
    proj = projects[0]
    if sync_running():
        sys.exit("A sync.py process is running. Wait for it to finish, then retry.")

    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"=== {mode}: {old} → {new} ({proj.name}, {proj.root}) ===")

    # 1. Asana
    state = sync.load_ids(proj)
    field_gid = state.get("custom_field_gid") or sync.SHARED_FIELD_GID
    if not field_gid:
        sys.exit("No Local ID field GID for this project")
    tasks = fetch_all_tasks(proj.gid, field_gid)
    todo = [t for t in tasks if rename_id(t["_local_id"], old, new) != t["_local_id"]]
    print(f"Asana: {len(todo)} of {len(tasks)} tasks hold {old}-NNN")
    failed = []
    for t in todo:
        lid = rename_id(t["_local_id"], old, new)
        if args.apply:
            try:
                sync._put(f"/tasks/{t['gid']}", {"data": {"custom_fields": {field_gid: lid}}})
            except Exception as e:
                failed.append((t["gid"], t["_local_id"], str(e)))
                continue
        print(f"  {t['_local_id']} → {lid}  {t.get('name', '')[:60]}")
    if failed:
        print(f"\n{len(failed)} Asana write(s) FAILED — local files NOT changed, prefix NOT switched:")
        for f in failed:
            print(f"  {f[1]} ({f[0]}): {f[2]}")
        print("Fix and re-run; already-renamed tasks are skipped.")
        sys.exit(1)

    # 2 + 3. Local state and mirrors, across every registered project
    for entry in sync.load_projects_registry():
        root = Path(entry["path"]).expanduser()
        ids_file, mirror = root / "asana-ids.json", root / "asana-mirror.md"
        if ids_file.exists():
            n, data = rewrite_ids_file(ids_file, old, new)
            if n:
                print(f"{ids_file}: {n} ID(s)")
                if args.apply:
                    ids_file.write_text(json.dumps(data, indent=2))
        if mirror.exists():
            text, n = rewrite_mirror(mirror.read_text(), old, new)
            if n:
                print(f"{mirror}: {n} line(s)")
                if args.apply:
                    mirror.write_text(text)

    # 4. Switch the prefix
    claude_md = proj.root / "CLAUDE.md"
    text, n = re.subn(rf"^(ASANA_TASK_PREFIX:[ \t]*){re.escape(old)}[ \t]*$", rf"\g<1>{new}", claude_md.read_text(), flags=re.M)
    if n != 1:
        sys.exit(f"Could not find 'ASANA_TASK_PREFIX: {old}' in {claude_md}")
    print(f"{claude_md}: ASANA_TASK_PREFIX {old} → {new}")
    if args.apply:
        claude_md.write_text(text)

    print("\nDone." if args.apply else "\nDry run only. Re-run with --apply.")


if __name__ == "__main__":
    main()
