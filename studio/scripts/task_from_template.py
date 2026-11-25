#!/usr/bin/env python3
"""
Create an Asana task with nested, ordered subtasks from a YAML template.

Built for repeatable checklists such as a release test task: the template
holds the generic sections (smoke test, pipeline checks, post-deploy checks),
and a release-specific items file is spliced in where the template says
`- insert: items`.

All writes go through sync.py's bainbot helpers, and the parent task gets a
local ID and a mirror entry exactly like `sync.py --create-task`.

Template format (YAML):

    name: "Test release {version} on staging"
    notes: |
      Short description - purpose and key links only.
    numbered: true            # prefix top-level subtasks with 1., 2., ...
    subtasks:
      - name: Pipeline + ACF sync
        notes: |
          Steps for this subtask.
        subtasks:             # optional, nested to any depth
          - name: ...
      - insert: items         # release-specific items go here (--items)
      - name: Smoke test
        ...

The items file is a YAML list of subtask entries in the same format.
`{placeholders}` in any name or notes are filled from --var key=value.

Usage:
    task_from_template.py TEMPLATE.yaml --project KF-WEB --var version=2.13.0 \\
        [--items release-items.yaml] [--section DOING] [--due 2026-10-20] \\
        [--assignee GID] [--blocks TASK_GID] [--dry-run]

    # Add a template's subtasks under an existing task instead of creating one:
    task_from_template.py TEMPLATE.yaml --under TASK_GID --var ...

Subtasks are assigned to nobody; the parent goes to --assignee (default: Mark).
"""

import argparse
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sync  # noqa: E402

MARK_GID = "507443625075"


class _Vars(dict):
    def __missing__(self, key):
        raise SystemExit(f"Template uses {{{key}}} but no --var {key}=... was given.")


def fill(text, variables):
    # Only touch {word} placeholders, so JSON or code in notes survives.
    return re.sub(r"\{(\w+)\}", lambda m: str(variables[m.group(1)]), text or "")


def expand(entries, items):
    out = []
    for entry in entries:
        if isinstance(entry, dict) and entry.get("insert") == "items":
            out.extend(items)
        else:
            out.append(entry)
    return out


def create_subtasks(parent_gid, entries, variables, numbered, dry_run, depth=1):
    """Create entries under parent_gid, top to bottom, recursing into children."""
    previous = None
    for i, entry in enumerate(entries, start=1):
        name = fill(entry["name"], variables)
        if numbered:
            name = f"{i}. {name}"
        notes = fill(entry.get("notes", ""), variables).strip()
        indent = "  " * depth
        if dry_run:
            print(f"{indent}- {name}")
            gid = f"dry-{depth}-{i}"
        else:
            gid = sync._post(f"/tasks/{parent_gid}/subtasks",
                             {"data": {"name": name, "notes": notes}})["data"]["gid"]
            # Asana inserts new subtasks at the top; pin each one after the last.
            position = {"insert_after": previous} if previous else {"insert_before": None}
            sync._post(f"/tasks/{gid}/setParent", {"data": {"parent": parent_gid, **position}})
            print(f"{indent}- {name}")
        previous = gid
        children = entry.get("subtasks") or []
        if children:
            create_subtasks(gid, children, variables, entry.get("numbered", False),
                            dry_run, depth + 1)


def set_mirror_assignee(proj, lid, assignee_gid, assignee_name):
    """Keep the mirror in step with Asana so a later sync does not revert it."""
    mirror = proj.mirror_file
    if not mirror.exists():
        return
    text = mirror.read_text()
    start = text.find(f"### {lid} ")
    if start < 0:
        return
    end = text.find("\n### ", start + 4)
    end = len(text) if end < 0 else end
    block = re.sub(r"- \*\*Assignee:\*\* .*", f"- **Assignee:** {assignee_name} ({assignee_gid})",
                   text[start:end], count=1)
    mirror.write_text(text[:start] + block + text[end:])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("template")
    ap.add_argument("--items", help="YAML list spliced in at '- insert: items'")
    ap.add_argument("--var", action="append", default=[], metavar="KEY=VALUE")
    ap.add_argument("--project", help="ASANA_TASK_PREFIX of the target project")
    ap.add_argument("--under", metavar="TASK_GID", help="add subtasks to this existing task instead")
    ap.add_argument("--section", default="NEXT UP")
    ap.add_argument("--due", default="")
    ap.add_argument("--assignee", default=MARK_GID)
    ap.add_argument("--blocks", metavar="TASK_GID", help="the new task blocks this task")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    template = yaml.safe_load(Path(args.template).read_text())
    items = yaml.safe_load(Path(args.items).read_text()) if args.items else []
    variables = _Vars(kv.split("=", 1) for kv in args.var)
    entries = expand(template.get("subtasks", []), items or [])
    numbered = template.get("numbered", False)

    if args.under:
        print(f"Adding to task {args.under}:")
        create_subtasks(args.under, entries, variables, numbered, args.dry_run)
        return

    if not args.project:
        ap.error("--project is required unless --under is given")
    projects = sync.discover_projects(filter_prefix=args.project)
    if not projects:
        ap.error(f"No project found with prefix '{args.project}'")
    proj = projects[0]

    name = fill(template["name"], variables)
    notes = fill(template.get("notes", ""), variables).strip()
    print(f"{proj.prefix}: {name}")
    if args.dry_run:
        print(notes, "\n")
        create_subtasks(None, entries, variables, numbered, dry_run=True)
        return

    lid = sync.create_task_full(proj, name, section_name=args.section, notes=notes, due=args.due)
    task_gid = next(g for g, l in sync.load_ids(proj)["tasks"].items() if l == lid)

    user = sync._get(f"/users/{args.assignee}", {"opt_fields": "name"})["data"]
    sync._put(f"/tasks/{task_gid}", {"data": {"assignee": args.assignee}})
    set_mirror_assignee(proj, lid, args.assignee, user["name"])
    if args.blocks:
        sync._post(f"/tasks/{args.blocks}/addDependencies", {"data": {"dependencies": [task_gid]}})

    create_subtasks(task_gid, entries, variables, numbered, dry_run=False)
    print(f"\n{lid} assigned to {user['name']}: "
          f"https://app.asana.com/1/{sync.WORKSPACE_GID}/project/{proj.gid}/task/{task_gid}")


if __name__ == "__main__":
    main()
